# Spike: esphome-audio-stack on the ESP32-S3-BOX-3

Branch `audio-stack`, measured on hardware 2026-07-26 and 2026-07-27 against
[n-IA-hane/esphome-audio-stack](https://github.com/n-IA-hane/esphome-audio-stack)
`v2026.7.0`, ESPHome 2026.7.1.

**Verdict: it works, and the BOX-3 has the hardware echo reference this needs.**
Full duplex on the shared bus, audio out of the speaker, a reference channel
captured in the same TDM frame as the microphones, a complete conversation on
top of it, and barge-in. Nothing has been migrated yet; `base/core.yaml` is
untouched.

Three spikes, in order: the hardware question, the assistant, the wake word.

## The answer this spike was built to get

**Yes, and it is slot 1.**

The test that settles it is the amplifier: switch it off, so the room hears
nothing, and play. Then the only thing that can still move a channel is an
electrical path.

| slot | quiet | tone, amplifier OFF |
|---|---|---|
| 0 | -42.5 dB | -41.7 dB |
| 1 | -59.3 dB | **-0.9 dB** |
| 2 | -42.4 dB | -41.1 dB |
| 3 | -82.5 dB | -82.6 dB |

Slots 0 and 2 are the microphones: with the amplifier off they do not move,
and with it on they rise together by 8 to 10 dB, which is the room hearing the
speaker. Slot 3 sits at the noise floor throughout. Slot 1 jumps nearly sixty
decibels to almost full scale **while the speaker is silent**, which only a DAC
feedback line can do.

Set `tdm_ref_slot: 1` and the stack confirms it: `TDM hardware reference -
slot 1 is echo ref`, `Audio task started (tdm=YES/ref)`, and the runtime state
alternates `mic` / `duplex` around each playback.

## Two configuration facts that cost the evening

Both were mine, not the component's. It reported no error for either.

**32 bits at 48 kHz kills the I2S init.** The topology 6.3 example uses
`bits_per_sample: 32` with `slot_bit_width: 32`. On this board that fails inside
`setup()`, and every later start refuses with `Cannot enable I2S from error
state` / `Failed to start I2S`. **16 bits in 16-bit slots works.**

**A 16 kHz bus plays nothing, silently.** With `sample_rate: 16000` the speaker
platform still declares 48 kHz, the log says `rate_conversion=1x`, and the
result is a device that logs a healthy playback and makes no sound at all. Set
the bus to 48 kHz - `rate_conversion=3x` appears, and so does the audio. This
cost two hours and one wrong conclusion, which is why it is written down.

Working combination, all four values together:

```yaml
sample_rate: 48000        # the bus, and what the speaker is fed
output_sample_rate: 16000 # what the microphone hands to the AFE
bits_per_sample: 16
slot_bit_width: 16
use_tdm_reference: true
tdm_total_slots: 4
tdm_mic_slot: 0
tdm_ref_slot: 1           # measured, see above
tdm_tx_slot: 0
```

## Two tooling lessons

**Setup-time logs never reach the network.** The API server starts after
`setup()`, so the error that put the audio stack into its error state was
invisible to every API log subscription - the first thing visible was the
refusal, long after the cause. USB serial is the only way to read it, and on the
BOX-3 the data port is the USB-C **on the module**, not the one on the dock.

**`esphome logs --device COM8` is broken on Windows**, raising
`FileNotFoundError` out of `subprocess`. Reading the port directly with pyserial
works and produced every boot log quoted here.

## Spike 2: the assistant, and barge-in

A full conversation runs on this stack: wake word, speech to text, intent,
spoken answer, and the wake word restarting itself.

**Barge-in works, which is the entire point of the migration.** Home Assistant's
own history, two entities, one clock:

| time | entity | state |
|---|---|---|
| 09:04:45 | media_player | playing |
| 09:05:08 | assist_satellite | **listening** |
| 09:05:13 | media_player | idle |
| 09:05:14 | assist_satellite | processing |
| 09:05:18 | assist_satellite | responding |

The satellite started listening five seconds **before** the speaker stopped. The
kitchen firmware cannot do this at all: microphone and speaker share one I2S bus,
so the wake word is stopped outright for the duration of any playback.

One thing this file has to say plainly, because it is not obvious from the
component: `voice_assistant: micro_wake_word: mww` does **not** start a pipeline
by itself. The core calls `voice_assistant.start` explicitly from
`on_wake_word_detected`, and a spike without that trigger detects the wake word
five times in a minute while the satellite sits at `idle` in Home Assistant.

## Spike 3: the wake word was never the weak part

The detection numbers looked bad and were read wrongly, here and in two commit
messages. On this stack the same words gave **maxima of 0.85 to 0.98 but a
three-frame average of 0.37 to 0.60**, against 0.60 to 0.79 on the kitchen
firmware, and that was written down as "detection is weaker after AEC".

It is not. **The peak is one frame wide, and averaging over three frames diluted
it.** With `sliding_window_size: 1` and the production cutoff of 0.6, measured
on hardware 2026-07-27 at 20:47, ten deliberate "Alexa" from the usual spot,
three seconds apart:

| # | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|
| score | 0.82 | 0.64 | 0.91 | 0.79 | 0.95 | 0.68 | 0.96 | 0.91 | 0.89 | 0.72 |

**Ten out of ten**, median 0.89, weakest 0.64 against a cutoff of 0.60, and not
one ring buffer warning in the window. What was called weak detection was an
averaging window that did not fit the signal.

Two hypotheses died on the way and are recorded so nobody pays for them twice.
The microphone stream is **not** being torn: `micro_wake_word` logs a warning
whenever its ring buffer overflows and gets reset, and across every measurement
window that line never appeared. The full AFE was **not** the problem either:
swapping `esp_afe` for `esp_aec`, which drops noise suppression, AGC and VAD and
keeps only echo cancellation, moved the numbers by less than the spread between
two utterances.

A gain sweep from +24 to -6 dB found no trend, so level is not the knob; the
window was.

## And the price of that window, also measured

**Two false wakes in forty minutes of listening at the production cutoff**, in a
lived-in kitchen on 2026-07-28, with the owner confirming he had not said the
wake word. One more at a cutoff of 0.45. In normal mode each of those starts a
conversation, so the one-frame window is not shippable as it stands.

The first false wake with a recorded score came in at **0.72**, which is the
worst case for the cheap fix. A cutoff high enough to reject it, 0.75, also
drops three of the ten real words above (0.64, 0.68, 0.72).

Untried, and both settable live: the other AEC modes (`sr_high_perf`,
`fd_low_cost`) and a lower hardware `Mic gain`. Every number in this file was
taken on `sr_low_cost` at 24 dB, so the front end has had exactly one setting
across the whole spike.

Measuring this needs the counter on the device, not a log subscription: the
first overnight attempt hung on a socket from a laptop that went to sleep, and
produced no number at all while printing a coverage figure that looked fine.

## The tuning instrument this left behind

`spike-va-duplex.yaml` now carries three knobs that work **live, without a
rebuild**, because every earlier step cost a three minute compile and an upload:

| entity | range | what it reaches |
|---|---|---|
| Prog wykrywania | 0.20 to 0.95 | `set_probability_cutoff` on every model |
| Wzmocnienie mww | 1 to 16 | `gain_factor` in front of the model, with clipping |
| Tryb AEC | three modes | reconfigures the canceller without a restart |

Plus a `Tryb strojenia` switch that cuts the conversation out: a detection is
only counted, and the wake word is not stopped after a hit
(`set_stop_after_detection(false)`, which YAML can only set at compile time).
Without it a series of ten words measures the first one and nine silences,
because the pipeline holds the microphone for a dozen seconds.

None of the three restores from flash, and each starts at the value compiled
into the file. That is deliberate: a knob that came back from flash at some
half-remembered value would silently falsify the next measurement.

## What migrating would buy, and what it would cost

Buy: barge-in and echo cancellation, neither of which this project has today,
plus the removal of everything `base/core.yaml` does to keep one bus half
duplex - stopping the wake word before the beep, waiting for `not
speaker.is_playing`, the `wake_start_pending` window, and cutting the amplifier
for External replies.

Cost: sixteen references to `box_mic`, `box_speaker` and `speaker_media_player`
in the core, and they carry the most expensive lessons in the repository. That
is a branch with a full re-test, not a refactor along the way.

Measured since this was first written: the AEC does cancel well enough to wake
the box while it is talking, see spike 2. What is left before the migration is
worth starting is the false wake rate at a one-frame window, and nothing else on
this list.

## One tooling lesson that cost two hours

**"OTA successful" is not proof that the firmware changed.** On this branch OTA
reported success and left the device running an eight hour old build through
several flashes, which is why a trigger that was in the file "did not fire": it
was not on the device. Check `device_info().compilation_time` after every
upload, and when it does not move, flash over USB with
`esphome upload <config> --device COM8` and the USB-C port **on the module**,
not the one on the dock.
