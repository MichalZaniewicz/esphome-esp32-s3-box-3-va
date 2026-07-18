# Changelog

## Unreleased

First build. A port of the upstream
[`esphome/wake-word-voice-assistants`](https://github.com/esphome/wake-word-voice-assistants)
ESP32-S3-BOX-3 config, rebuilt as a package + thin-config repo.

**Not yet confirmed on hardware.** Everything below is written and passes the
offline validator; nothing has been flashed.

### Changed from upstream

- **The display layer is LVGL, not `display:` + `pages:`.** Same phases and same
  illustrations, but as LVGL pages, with the GT911 touchscreen wired in. The two
  approaches cannot coexist in one ESPHome config, so this is a replacement.
- **`voice_assistant:` no longer has a `media_player:`.** With one attached,
  ESPHome fetches and decodes the TTS URL on-device at `TTS_END` in addition to
  anything `on_tts_end` does; on long replies that rebooted the box. Routing is
  now explicit in the `TTS output` select (`This device` / `External player` /
  `Both`). Timer sounds and HA announcements still go through the
  `speaker_media_player` component.
- **Illustrations are `RGB565`** instead of 24-bit `RGB`, matching LVGL's colour
  depth: no conversion at draw time and ~150 KB of flash each instead of ~230 KB.
- **Timer UI moved to LVGL's top layer**, so the countdown and progress strip
  survive page changes instead of being redrawn per page. A running timer is
  green, a paused one blue.
- **`extra_glyphs`** replaces upstream's giant unused `allowed_characters`
  substitution — upstream defined it but never referenced it, so non-Latin
  characters never actually reached the font.
- **The `Timer ringing` switch is exposed** to Home Assistant rather than
  `internal:`, so an automation can silence a timer ringing in an empty room.

### Added

- Tap-to-talk: a tap anywhere on the idle page, or on the GT911 "home" button
  under the screen, starts a pipeline without a wake word.
- Tapping the timer-ringing screen silences it.
- `time: platform: homeassistant`, as groundwork for anything clock-driven.
- `docs/HARDWARE.md`, `scripts/validate.py`, `scripts/esplog.py` and a Claude
  Code skill.
