# Changelog

## Unreleased

First build. A port of the upstream
[`esphome/wake-word-voice-assistants`](https://github.com/esphome/wake-word-voice-assistants)
ESP32-S3-BOX-3 config, rebuilt as a package + thin-config repo.

**Confirmed working on hardware** (ESPHome 2026.7.0, flashed over OTA): wake
word, speech to text, replies routed to an external speaker, voice timers and
their alarm, the touchscreen, the home screen and the animated character.

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
  substitution - upstream defined it but never referenced it, so non-Latin
  characters never actually reached the font.
- **The `Timer ringing` switch is exposed** to Home Assistant rather than
  `internal:`, so an automation can silence a timer ringing in an empty room.

### Fixed

- **The talking face stopped a moment after the reply started**, while the
  external speaker had not begun yet. Attaching the media player again woke two
  handlers that nothing had been triggering before: at `TTS_END` the assistant is
  already `IDLE`, so `on_announcement` treated the reply as ordinary playback and
  switched to the muted screen, and stopping that playback fired `on_idle`, which
  ended the talking face and restarted the wake word. Both are now gated on a
  reply being in progress, which also stops the wake word listening to the
  speaker's own voice.
- **Cast latency.** A speaker handed a URL takes about a second to start, and the
  box was already animating. `tts_hold_lead_ms` adds that to the hold so the
  mouth is still moving when the reply ends.

- **The wake word never fired** while tap-to-talk dictation worked perfectly.
  Fixed by dropping `vad:`. The evidence: with the cutoff lowered to 0.50 the
  component logged nothing at all, but with VAD removed the same utterance logs
  `sliding average probability is 0.56 and max probability is 1.00`. The model
  recognises the word perfectly - `max` hits 1.00 - but the cutoff is compared
  against the average over the sliding window, and three networks per frame
  (alexa + okay_nabu + VAD) appear not to fit the real-time budget, so dropped
  frames held that average below even a 0.50 cutoff. Note the default cutoff is
  0.90, which this hardware never reaches.
- Wake word input gain (`gain_factor: 4` on mWW's microphone source, tunable via
  `mww_gain_factor`) matching `home-assistant-voice-pe`. This was first committed
  as a fix for the above and **was not the cause** - the wake word failed
  identically at 1 and 4. Kept because the reference hardware ships it, but its
  effect here is unmeasured.

- **A ringing timer blanked the screen** instead of showing the timer-finished
  page. The alarm is itself an announcement, so `media_player: on_announcement:`
  treated it as user-initiated playback and switched to the muted (black) page,
  clobbering the phase `on_timer_finished` had just set. Upstream avoided this by
  waiting for `media_player.is_announcing` before setting the phase; this instead
  guards the announcement handler on `timer_ringing` being off, which does not
  depend on event ordering.
- **`Parent bus is busy` when a timer started ringing.** The microphone still held
  the I2S bus - `on_announcement` stops the wake word only once playback has
  begun - so the speaker's first start failed and retried a second later. The
  `timer_ringing` switch now stops the wake word and waits for the microphone to
  release the bus before playing.

- **The timer alarm always rings on the box**, independently of the `TTS output`
  select. Briefly it followed that select, which was the wrong model: a reply
  should come out wherever you listen, but an alarm has to be insistent and
  interruptible. Locally it repeats until silenced and a tap on the screen stops
  it; on a remote speaker it plays once, with no way for the box to know when it
  finished or to cut it short. Note this means a muted `speaker_media_player`
  entity silences the alarm.

- **`image:` migrated to the platform syntax** (`platform: file`). The old
  top-level form is deprecated and removed in ESPHome 2027.1.0. That syntax
  landed in 2026.7.0, so `min_version` moves there too - a real cost, since it
  shuts out 2026.4-2026.6, but the alternative is a warning on every build for
  the next six months and a hard break later.

- **A boot animation.** The starting screen was a line of static text. Three dots
  now travel under it, the lit one growing and going fully opaque, all three
  cross-fading through a palette a third of a cycle apart so no two share a
  colour. `boot_palette` takes any number of `0xRRGGBB` entries. It costs two
  properties on three widgets six times a second, and only while that page is
  showing - after boot the interval does nothing at all.

### Removed

- **The per-phase illustrations.** Nine full-screen PNGs, every one of them
  hidden the moment a character package is installed. The core now compiles a
  single image - the character - and falls back to plain text status pages when
  no package claims a phase. Those pages are meant to be plain: the core has to
  work before any optional screen is up, and looking good is `base/faces/`' job.

  Measured on an S3-Box-3: **51% → 25.5% of flash** (2,075,531 of 8,126,464
  bytes), RAM 37%. Worth being clear that this was not a rescue - at 51% there
  was plenty of room. It buys headroom for screens to come, and stops the repo
  shipping 2 MB of artwork nobody sees.

- **A wake sound**, with a `Wake sound` switch in Home Assistant. It is 180 ms
  and generated for this repo rather than borrowed from Voice PE, whose own wake
  sound is 0.95 s: mic and speaker share a single I2S bus here, so the beep has
  to finish before the assistant can open the microphone, and a second of that
  is a second of the user's sentence lost.

### Added

- Tap-to-talk: a tap anywhere on the idle page, or on the GT911 "home" button
  under the screen, starts a pipeline without a wake word.
- Tapping the timer-ringing screen silences it.
- `time: platform: homeassistant`, as groundwork for anything clock-driven.
- `docs/HARDWARE.md`, `scripts/validate.py`, `scripts/esplog.py` and a Claude
  Code skill.
