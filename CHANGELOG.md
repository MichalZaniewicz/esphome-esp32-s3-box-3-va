# Changelog

## Unreleased

First build. A port of the upstream
[`esphome/wake-word-voice-assistants`](https://github.com/esphome/wake-word-voice-assistants)
ESP32-S3-BOX-3 config, rebuilt as a package + thin-config repo.

**Builds and boots on hardware** (ESPHome 2026.7.0, OTA). Functional behaviour —
screen contents, touch, the assistant itself — is not confirmed yet.

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

### Fixed

- **The wake word never fired** while tap-to-talk dictation worked perfectly.
  `micro_wake_word` runs inference on the raw microphone stream, so it gets none
  of `voice_assistant`'s `auto_gain` / `volume_multiplier` — those are applied by
  Home Assistant to the STT stream. On a quiet mic that means clean transcription
  and a wake word that never reaches its cutoff. Now sets `gain_factor: 4` on
  mWW's microphone source, matching `home-assistant-voice-pe`; tunable via the
  `mww_gain_factor` substitution. Upstream does not set it, so any straight port
  of that config inherits the default of 1.

- **A ringing timer blanked the screen** instead of showing the timer-finished
  page. The alarm is itself an announcement, so `media_player: on_announcement:`
  treated it as user-initiated playback and switched to the muted (black) page,
  clobbering the phase `on_timer_finished` had just set. Upstream avoided this by
  waiting for `media_player.is_announcing` before setting the phase; this instead
  guards the announcement handler on `timer_ringing` being off, which does not
  depend on event ordering.
- **`Parent bus is busy` when a timer started ringing.** The microphone still held
  the I2S bus — `on_announcement` stops the wake word only once playback has
  begun — so the speaker's first start failed and retried a second later. The
  `timer_ringing` switch now stops the wake word and waits for the microphone to
  release the bus before playing.

### Added

- Tap-to-talk: a tap anywhere on the idle page, or on the GT911 "home" button
  under the screen, starts a pipeline without a wake word.
- Tapping the timer-ringing screen silences it.
- `time: platform: homeassistant`, as groundwork for anything clock-driven.
- `docs/HARDWARE.md`, `scripts/validate.py`, `scripts/esplog.py` and a Claude
  Code skill.
