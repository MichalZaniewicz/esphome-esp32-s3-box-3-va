# ESP32-S3-BOX-3 — hardware notes

Everything here is what `base/core.yaml` assumes. The pin map is taken from
Espressif's own board support package,
[`esp-bsp/bsp/esp-box-3`](https://github.com/espressif/esp-bsp/tree/master/bsp/esp-box-3)
(`include/bsp/esp-box-3.h`), not from forum folklore.

## Board

| | |
|---|---|
| SoC | ESP32-S3, 240 MHz, dual core |
| Flash | 16 MB |
| PSRAM | octal, 80 MHz — **mandatory**: the `mipi_spi` `S3BOX` model declares `requires: psram`, and the LVGL draw buffer lives there |
| Display | 320x240 SPI, ILI9341-class |
| Touch | GT911 capacitive, I2C |
| Audio out | ES8311 DAC + amplifier + speaker |
| Audio in | ES7210 ADC, dual microphone array |
| ESPHome board | `esp32s3box` |

Note the revision split: the older **ESP32-S3-BOX** and **BOX-Lite** use a
**TT21100** touch controller and an ST7789 panel. The **BOX-3** uses the GT911
and an ILI9341-class panel — `esp-box-3.c` probes GT911 first and picks the panel
driver from what answers. A config for the older boxes will not drive this one.

## Pin map

| Function | GPIO | Notes |
|---|---|---|
| I2C SDA | 8 | Shared bus: ES7210 + ES8311 + GT911 |
| I2C SCL | 18 | |
| LCD CLK | 7 | |
| LCD MOSI | 6 | |
| LCD CS | 5 | |
| LCD DC | 4 | |
| LCD RST | 48 | Active low → `inverted: true`. Also resets the GT911 |
| Backlight | 47 | PWM via `ledc` |
| Touch INT | 3 | Strapping pin (JTAG source select) → `ignore_strapping_warning` |
| I2S MCLK | 2 | |
| I2S BCLK | 17 | |
| I2S LRCLK | 45 | Strapping pin |
| I2S DOUT | 15 | ESP → ES8311 (speaker) |
| I2S DIN | 16 | ES7210 → ESP (microphones) |
| Amplifier enable | 46 | Active high, strapping pin |
| Top button | 0 | `INPUT_PULLUP`, `inverted: true`, strapping pin |
| Mute button | 1 | Present in esp-bsp (`BSP_BUTTON_MUTE_IO`); **not used here** — see below |
| Dock I2C | 40 / 41 | Only when sitting in an accessory dock |

The red circle silkscreened under the screen is **not a GPIO**. It is touch
button 0 on the GT911, read with `binary_sensor: platform: gt911, index: 0`.

## Gotchas

**LVGL replaces `display: pages:`, it does not extend it.** The display block
must carry `update_interval: never` and `auto_clear_enabled: false`, and must
have no `lambda:` or `pages:` — LVGL owns the framebuffer. This is why porting
the upstream voice config to a touch UI means rewriting the whole display layer.

**Do not declare `reset_pin: 48` on the touchscreen.** The LCD reset net also
resets the GT911, and esp-bsp drives no separate touch reset (`rst_gpio_num =
GPIO_NUM_NC`). Declaring GPIO48 on both components has them pulse reset against
each other. Instead the touchscreen gets `setup_priority: -200`, so it
initialises after the display's own reset pulse has already brought the GT911 up.

**Do not add `mirror_x` / `mirror_y` / `swap_xy` to the display.** The `S3BOX`
model in `mipi_spi` already bakes in `mirror_x + mirror_y` and BGR colour order
(`esphome/components/mipi_spi/models/ili.py`). Adding your own transform
double-applies it. If the *touch* axes come out wrong, fix them on the
`touchscreen:` block, not the display.

**The GT911 address is strap-selected at reset.** The driver probes 0x5D and
falls back to 0x14, so no address is set here. If touch dies specifically after a
warm boot, this is the first thing to look at.

**`show_test_card: true` is rejected** whenever `update_interval: never`, so you
cannot use it to smoke-test the panel from an LVGL config. Test with a
throwaway non-LVGL config instead.

**GPIO0, 3, 45 and 46 are strapping pins.** Each needs
`ignore_strapping_warning: true` or the build warns.

**GPIO1 (mute) is deliberately unused.** esp-bsp defines it as both
`BSP_BUTTON_MUTE_IO` and `BSP_MUTE_STATUS`, and whether it reads a momentary
button or a latched slider differs between BOX-3 units. Upstream ESPHome ignores
it too and exposes a template `Mute` switch instead. Probe it on your own unit
before relying on it.

**The mmWave radar is not on the BOX-3.** It lives on the separate
ESP32-S3-BOX-3-SENSOR dock, reachable over the dock I2C on GPIO40/41, along with
temperature/humidity, IR and a microSD slot. Nothing in this config touches it.

## Audio layout

Unlike boards that wire an ADC and a DAC to separate buses over shared clock
pins, the BOX-3 puts both codecs on one I2S bus. That means no master/slave
trickery is needed: a single `i2s_audio` bus, the ES7210 capturing at 16 kHz for
the wake word, the ES8311 playing back at 48 kHz, both stock ESPHome components.

The speaker has a **single output channel** (`channel: left`), which is also why
the announcement pipeline is configured with `num_channels: 1`.
