---
name: esp32-s3-box-3
description: >
  Reference for building/editing ESPHome configs on the Espressif ESP32-S3-BOX-3
  (ESP32-S3 voice devkit: 320x240 SPI panel, GT911 capacitive touch, ES8311 codec,
  ES7210 dual-mic ADC). Use whenever working on this board or on the base/core.yaml
  in this repo: correct pinout, the LVGL-vs-`display: pages:` constraint, the shared
  LCD/touch reset net, why voice_assistant deliberately has no media_player, and the
  BOX-3 vs BOX/BOX-Lite revision split.
---

# ESP32-S3-BOX-3: ESPHome working notes

Pin facts are from Espressif's own BSP,
[`esp-bsp/bsp/esp-box-3`](https://github.com/espressif/esp-bsp/tree/master/bsp/esp-box-3),
cross-checked against the upstream ESPHome voice config. Full detail:
`docs/HARDWARE.md` in this repo.

## Board

- **ESP32-S3**, 240 MHz, **16 MB flash**, **octal PSRAM** (mandatory — see below).
- **320x240 SPI panel**, ILI9341-class. ESPHome: `mipi_spi`, `model: S3BOX`.
- **GT911** capacitive touch on the shared I2C bus.
- **ES8311** DAC + amp + speaker (single channel), **ES7210** dual-mic ADC.
- ESPHome target: `board: esp32s3box`, `flash_size: 16MB`, framework `esp-idf`.

**Revision trap:** the older **ESP32-S3-BOX** and **BOX-Lite** use a **TT21100**
touch controller and an ST7789 panel; the **BOX-3** uses **GT911** + ILI9341.
`esp-box-3.c` probes GT911 first and selects the panel driver from what answers.
Configs for the older boxes do not drive this one, and `S3BOXLITE` is a different
`mipi_spi` model (RGB order, `mirror_x` only).

## Pinout

| Function | GPIO | | Function | GPIO |
|---|---|---|---|---|
| I2C SDA / SCL | 8 / 18 | | I2S MCLK / BCLK / LRCLK | 2 / 17 / 45 |
| LCD CLK / MOSI | 7 / 6 | | I2S DOUT (spk) / DIN (mic) | 15 / 16 |
| LCD CS / DC | 5 / 4 | | Amplifier enable | 46 |
| LCD RST | 48 (active low) | | Top button | 0 |
| Backlight | 47 | | Mute button (unused) | 1 |
| Touch INT | 3 | | Dock I2C | 40 / 41 |

One I2C bus carries ES7210 + ES8311 + GT911. **GPIO 0, 3, 45 and 46 are strapping
pins** — each needs `ignore_strapping_warning: true`.

The red circle under the screen is **not a GPIO**: it is GT911 touch button 0,
read with `binary_sensor: platform: gt911, index: 0`.

## The gotchas that cost time

**LVGL and `display: pages:` are mutually exclusive.** Under LVGL the display
block needs `update_interval: never` and `auto_clear_enabled: false`, and must
carry no `lambda:` or `pages:`. The upstream `wake-word-voice-assistants` S3-Box-3
config is built entirely on `display: pages:` + `display.page.show`, so making it
touch-driven means *replacing* the display layer, not extending it. Budget for
that before promising a quick port.

**Never declare `reset_pin: 48` on the `touchscreen:` block.** The LCD reset net
also resets the GT911, and esp-bsp drives no separate touch reset
(`rst_gpio_num = GPIO_NUM_NC`). Two components pulsing GPIO48 fight each other.
Give the touchscreen `setup_priority: -200` instead, so it inits after the
display's reset pulse has already brought the GT911 up.

**Never add `mirror_x` / `mirror_y` / `swap_xy` to the display.** The `S3BOX`
model already bakes in `mirror_x + mirror_y` + BGR
(`esphome/components/mipi_spi/models/ili.py`); your own transform double-applies.
Wrong *touch* axes are fixed on the `touchscreen:` block, not the display.

**PSRAM is not optional.** The `S3BOX` model declares `requires: psram`, and the
LVGL draw buffer lives there. A missing `psram:` block is a hard config error.

**`show_test_card: true` is rejected** with `update_interval: never`, so it is
unavailable in any LVGL config. Smoke-test the panel with a throwaway non-LVGL
config.

**GT911 address is strap-selected at reset** (0x5D or 0x14; the driver probes
both). Touch that works cold and dies on a warm boot points here.

**Change LVGL pages through the LVGL action, not `lv_scr_load()`.** The ESPHome
component tracks which page is current; loading a screen behind its back desyncs
that. Use `lvgl.page.show:` — which means phase→page dispatch is a chain of
`if:` blocks rather than one tidy C++ `switch`.

**`voice_assistant.get_timers()` returns `const std::vector<Timer> &`**, not a
map. Iterate the timers directly; `pair.second` does not compile.

## Wake word never fires, but dictation works perfectly

Classic and misleading: `micro_wake_word` sits in `DETECTING_WAKE_WORD`, the mic
is demonstrably fine (tap-to-talk transcribes speech correctly), and yet no
`Detected '<word>'` line ever appears.

The cause is that the two paths get different audio. `voice_assistant`'s
`noise_suppression_level`, `auto_gain` and `volume_multiplier` are **sent to Home
Assistant and applied there**, to the STT stream. `micro_wake_word` runs its
inference **on-device, on the raw microphone stream**, so it sees none of that
boost. A quiet mic therefore transcribes fine and never wakes.

The knob is `gain_factor` on mWW's own microphone source, default **1**:

```yaml
micro_wake_word:
  microphone:
    microphone: box_mic
    channels: 0        # defaults to 0 anyway
    gain_factor: 4     # what home-assistant-voice-pe ships
```

Range is 1-64. Too low and the wake word needs shouting at; too high and room
noise triggers it. Note the upstream `wake-word-voice-assistants` S3-Box-3 config
does **not** set it, so a straight port inherits `gain_factor: 1`.

Diagnosing: the component only logs successful detections and VAD-blocked ones
(`Wake word model predicts 'X', but VAD model doesn't.`). A near miss logs
nothing at all, so absence of logs tells you nothing about how close it got —
lower the model's `probability_cutoff` temporarily if you need to see the edge.

## Opacity has two scales

In YAML an opacity is a **percentage or an `LV_OPA_*` constant** (`bg_opa: 27%`,
`bg_opa: COVER`). In a lambda it is `lv_opa_t`, i.e. **0-255**:

```yaml
bg_opa: 27%                              # config
bg_opa: !lambda return on ? 255 : 70;    # runtime, same value
```

A bare `bg_opa: 90` in YAML fails validation with "Percentage value must use a
percent sign", which is clear enough once you see it - but the two scales look
identical while you are writing them, and an animation that sets opacity from a
lambda makes it easy to carry 0-255 thinking into the static config. Note the
offline validator cannot catch this: it checks YAML, substitutions and duplicate
ids, not component schemas.

## voice_assistant and TTS: the reboot trap

If `voice_assistant:` has a `media_player:`, ESPHome does not merely hand you the
URL at `TTS_END` — it *also* plays it itself
(`voice_assistant.cpp`: `media_player_->make_call().set_media_url(url)`), on top
of anything `on_tts_end` does. So a config that forwards TTS to an external HA
speaker in `on_tts_end` gets **both**: the external speaker plays it, and the box
independently downloads and decodes the same file. On long replies that local
decode is a plausible cause of mid-answer reboots.

Dropping `media_player:` from `voice_assistant:` does **not** disable TTS: the
pipeline request flags depend only on wake-word and VAD settings, so HA still
runs TTS and still fires `on_tts_end` with the URL. It just makes playback
explicit — route it yourself with `media_player.play_media` (local),
`homeassistant.service` (external), or both. Timer sounds and HA announcements
keep working through the `speaker_media_player` component, which exists
independently of the assistant.

## Not on this board

The **mmWave radar, temperature/humidity, IR and microSD are on the
ESP32-S3-BOX-3-SENSOR dock**, not the box, and hang off the dock I2C (GPIO40/41).
**GPIO1 (mute)** is defined in esp-bsp but its behaviour (momentary vs latched)
varies between units; upstream ESPHome ignores it and uses a template `Mute`
switch. Probe before relying on it. No software-controllable status LED could be
confirmed on the box itself.
