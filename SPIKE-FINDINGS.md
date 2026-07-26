# Spike: esphome-audio-stack on the ESP32-S3-BOX-3

Branch `audio-stack`, measured on hardware 2026-07-26 against
[n-IA-hane/esphome-audio-stack](https://github.com/n-IA-hane/esphome-audio-stack)
`v2026.7.0`, ESPHome 2026.7.1.

**Verdict: it works, and the BOX-3 has the hardware echo reference this needs.**
Full duplex on the shared bus, audio out of the speaker, and a reference channel
captured in the same TDM frame as the microphones. Nothing has been migrated
yet; `base/core.yaml` is untouched.

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

## What migrating would buy, and what it would cost

Buy: barge-in and echo cancellation, neither of which this project has today,
plus the removal of everything `base/core.yaml` does to keep one bus half
duplex - stopping the wake word before the beep, waiting for `not
speaker.is_playing`, the `wake_start_pending` window, and cutting the amplifier
for External replies.

Cost: sixteen references to `box_mic`, `box_speaker` and `speaker_media_player`
in the core, and they carry the most expensive lessons in the repository. That
is a branch with a full re-test, not a refactor along the way.

Still unmeasured: whether AEC actually cancels well enough to wake the box while
it is talking. That needs a voice test, not a tone.
