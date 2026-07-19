# ESPHome Voice Assistant for the ESP32-S3-BOX-3

A **Home Assistant voice satellite** for the
[ESP32-S3-BOX-3](https://github.com/espressif/esp-box), built on **LVGL and the
touchscreen** instead of the static full-screen images the stock config paints.
Pure ESPHome, no custom C firmware: an always-on core you pull as a package, plus
one thin config file you actually edit.

> **Status: initial build.** Ported from the upstream
> [`wake-word-voice-assistants`](https://github.com/esphome/wake-word-voice-assistants)
> S3-Box-3 config, rebuilt on LVGL + GT911, with the TTS path reworked (see
> below). Not yet confirmed on hardware — see [CHANGELOG.md](CHANGELOG.md).

## What it does

- **Voice assistant**: on-device wake word (`alexa`, `okay_nabu`) via
  `micro_wake_word`, the full Home Assistant Assist pipeline (STT / LLM / TTS),
  and a mic that mutes from HA.
- **LVGL UI**: one page per assistant phase — booting, idle, listening,
  thinking, replying, error, muted, no-Wi-Fi, no-HA, timer ringing — with the
  request and response text drawn over the illustration.
- **Touchscreen**: the GT911 is wired into LVGL. Tap anywhere on the idle screen
  for tap-to-talk; tap a ringing timer to silence it. That is deliberately a
  small surface: it is the base to build a real touch UI on, not the finished UI.
- **Timers**: set by voice, with a countdown and a progress strip on LVGL's top
  layer that stays visible across page changes (green while running, blue while
  paused).
- **TTS routing you choose at runtime**: the reply can come out of the box, out
  of an external Home Assistant media player, or both — see below.
- **Reskinnable**: every phase illustration is a substitution, so you can swap
  the artwork without touching the core.

## The TTS routing, and why it exists

`voice_assistant:` here has **no `media_player:`**, on purpose.

With one attached, ESPHome does not just hand you the TTS URL — at `TTS_END` it
*also* calls the media player with that URL itself
(`voice_assistant.cpp`: `media_player_->make_call().set_media_url(url)`), so the
box downloads and decodes the audio locally on top of anything you do in
`on_tts_end`. On long replies that local download-and-decode is what made the
device reboot mid-answer while an external speaker played the reply through.

Leaving it out changes nothing about the pipeline — the request flags sent to
Home Assistant don't depend on the media player, so HA still runs TTS and still
delivers the URL to `on_tts_end`. What changes is that **routing is explicit**,
in the `TTS output` select:

| Option | What happens |
|---|---|
| `This device` | The box speaks. Upstream behaviour, local decode included. |
| `External player` | Only `${external_media_player_id}` speaks. The box never fetches the file. |
| `Both` | Both, at the cost of the local decode. |

Timer sounds, Home Assistant announcements and Music Assistant are unaffected:
they go through the `speaker_media_player` component directly, which still
exists.

## Quick start

> Requires **ESPHome 2026.4.0+**.

1. Copy `secrets.example.yaml` to `secrets.yaml` and fill in your Wi-Fi.
2. Copy **`esp32-s3-box-3-va.yaml`** next to it and edit the `substitutions:` at
   the top (device name, timezone, external media player, artwork). That thin
   file is the only firmware file you keep; the core is pulled from GitHub at
   compile time, see its `packages:` block.
3. **First flash over USB**, then updates go wireless:
   ```
   esphome run esp32-s3-box-3-va.yaml
   ```
   Or drop both files into the ESPHome dashboard's `/config/esphome/` and hit
   Install.
4. In Home Assistant: the new ESPHome device appears, open **Configure** and
   assign an Assist pipeline.
5. Say "Alexa" (or "OK Nabu"), or just tap the screen.

After changing anything in the core, run `esphome clean` before the next build —
otherwise ESPHome reuses the cached copy of the remote package.

## Repository layout

```
esp32-s3-box-3-va.yaml     # YOUR config: copy + edit this (pulls the rest from GitHub)
secrets.example.yaml       # copy to secrets.yaml
base/
  core.yaml                # the always-on core, pulled as a remote package
docs/
  HARDWARE.md              # pinout, I2C map, gotchas
scripts/
  validate.py              # offline YAML check (syntax, substitutions, duplicate ids)
  esplog.py                # stream device logs over the native API
skill/
  esp32-s3-box-3/          # Claude Code skill: pinout + hard-won gotchas
```

## Configuration

Day-to-day settings are Home Assistant entities, not config edits: microphone
mute, screen brightness, TTS output, wake word engine location, and the timer
switch.

What lives in the thin config:

| Substitution | Default | What it does |
|---|---|---|
| `name` / `friendly_name` | `esp32-s3-box-3-va` / `S3 Box 3 Voice` | Device name. Changing `name` re-creates every entity in HA. |
| `posix_timezone` | `UTC0` | Clock zone in POSIX form (the device has no IANA database). Only a pre-sync fallback; HA owns the clock. |
| `external_media_player_id` | `media_player.living_room` | Where `External player` / `Both` send the reply. |
| `tts_output_default` | `This device` | Boot default of the `TTS output` select. |
| `volume_min` / `volume_max` | `0.5` / `0.8` | Media player clamps for the onboard speaker. |
| `hidden_ssid` | `false` | `true` enables `fast_connect` for a hidden SSID. |
| `*_illustration_file` | Casita artwork | The 320x240 PNG per phase. Any URL or local path. |
| `timer_finished_sound_file` | Voice PE `timer_finished.flac` | The timer alarm, baked into flash at compile time (so it rings without network). Any URL or local MP3/FLAC/WAV. The default points at another project's `dev` branch — override it for reproducible builds. |
| `font_glyphsets` / `extra_glyphs` | `GF_Latin_Core` / `²³` | Characters the UI can render. `GF_Latin_Core` is 319 glyphs and already covers Western *and* Central European accents, so most languages need nothing here. Note the Google Fonts glyphsets are increments, not supersets — `GF_Latin_Plus` (110 glyphs) is not a bigger `Core`, and swapping one for the other loses the accents. |
| `mww_gain_factor` | `4` | Input gain for the wake word only (1–64). Raise it if the wake word needs shouting at, lower it if room noise triggers it. |

Pins are substitutions too, but you should not need them unless you are porting
to another board.

## Why not the upstream config

[`esphome/wake-word-voice-assistants`](https://github.com/esphome/wake-word-voice-assistants)
ships a perfectly good S3-Box-3 config, and this started as a port of it. It
paints the screen with `display:` + `pages:` + full-screen PNGs and never
touches the touch panel. LVGL and `display: pages:` cannot coexist in one
ESPHome config, so anything touch-driven means replacing that layer rather than
extending it. A copy of the upstream file is worth keeping around for reference
while you do.

## Claude Code skill

This repo ships a [Claude Code](https://claude.com/claude-code) skill at
[`skill/esp32-s3-box-3/`](skill/esp32-s3-box-3/SKILL.md): the pinout, the LVGL
and GT911 constraints, and the gotchas that cost real debugging time. Install it
user-wide so any session picks it up:

```bash
cp -r skill/esp32-s3-box-3 ~/.claude/skills/
```

## Credits

- **[esphome/wake-word-voice-assistants](https://github.com/esphome/wake-word-voice-assistants)**:
  the original S3-Box-3 config and the Casita illustrations this is ported from.
- **[espressif/esp-bsp](https://github.com/espressif/esp-bsp)**: the authoritative
  BOX-3 pin map (`bsp/esp-box-3`).
- **ESPHome**: everything the firmware is built out of.
- **[Home Assistant Voice PE](https://github.com/esphome/home-assistant-voice-pe)**:
  the timer sound and the phase model.
