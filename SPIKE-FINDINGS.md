# Spike: esphome-audio-stack on the ESP32-S3-BOX-3

Branch `audio-stack`, measured on hardware 2026-07-26 against
[n-IA-hane/esphome-audio-stack](https://github.com/n-IA-hane/esphome-audio-stack)
`v2026.7.0`, ESPHome 2026.7.1.

**Verdict: not usable yet. The component initialises on this board, and then
plays nothing.** The half-duplex arrangement in `base/core.yaml` stays.

## What works

- **Both codecs are found and driven.** `esp_codec_dev backend ready
  (rx_codec=ES7210, tx_codec=ES8311)`, on the BOX-3's shared I2S bus with our
  own pinout (MCLK 2, BCLK 17, LRCLK 45, DIN 16, DOUT 15).
- **The stack reaches `running`** in both topologies: standard I2S, and TDM with
  a hardware reference (`TX/RX TDM channel initialized`, `TDM mode: 4 slots,
  mic_slot=0, ref_slot=2, mask=0xf`, `Audio task started (tdm=YES/ref)`).
- **The TDM slot sensors publish**, so the diagnostic path the component
  advertises for bring-up does what it says.

## What does not

- **No sound comes out, in either topology.** Tested with the amplifier enable
  held high, the media player at volume 1.0, and eight bursts of the 180 ms wake
  sound: nothing audible, twice, once per topology. Everything logs success
  while the room stays silent.
- Since nothing plays, **the question this spike existed to answer could not be
  answered**: which TDM slot carries the DAC feedback. The levels measured
  (slot 0 and slot 2 identical to within 0.1 dB, slot 1 about 26 dB lower, slot
  3 at the noise floor around -85 dB) are consistent with microphones picking up
  room noise and nothing else. With no playback there is no reference to find.

## The one configuration fact worth keeping

**32 bits at 48 kHz kills it.** The first attempt used
`bits_per_sample: 32`, `slot_bit_width: 32`, `sample_rate: 48000` with four TDM
slots, taken from the component's topology 6.3 example. That fails during
`setup()`: the I2S hardware ends in `ERROR`, and every later start refuses with
`Cannot enable I2S from error state` / `Failed to start I2S`.

The same topology at **16 bits, 16 kHz, `slot_bit_width: 16`** sets up cleanly.
So a report of "6.3 does not work" would be wrong; it is that combination.

## Two things that cost an hour, so they are written down

**Setup-time logs are invisible over the network.** The API server starts after
`setup()`, so the error that put the audio stack into its error state never
reaches an API log subscription - the first thing visible is the refusal, long
after the cause. Reading it needs USB serial.

**`esphome logs --device COM8` fails on Windows** with `FileNotFoundError`
raised out of `subprocess`. Reading the port directly with pyserial works and is
what produced everything above:

```
python serialread.py COM8 boot.log 35     # then reboot the device
```

## If this is picked up again

1. Ask the component's author whether ES8311 output is expected to work on a
   shared bus at all, and whether TDM TX to a mono DAC is supported - quoting the
   log lines above, which show a healthy init and a silent speaker.
2. If output can be made to work, the rest follows quickly: the slot question is
   one measurement, and a hardware reference would buy barge-in and echo
   cancellation, neither of which this project has today.
3. What full duplex would remove from `base/core.yaml`: stopping the wake word
   before the beep, the wait for `not speaker.is_playing`, the
   `wake_start_pending` window, and the amplifier cut for External replies.
