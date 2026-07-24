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
- **Routing is explicit, in the `TTS output` select** (`This device` /
  `External player` / `Both`), rather than implied by the hardware.

  `voice_assistant:` was going to drop its `media_player:` to stop ESPHome
  fetching and decoding the TTS URL on-device at `TTS_END`, which is the
  suspected cause of mid-answer reboots on long replies. **That did not survive
  contact with Home Assistant and the attachment is still there.**
  `get_feature_flags()` only advertises ANNOUNCE when a media player is present,
  and Home Assistant only asks a satellite for its configuration - the wake word
  list - inside `if feature_flags & ANNOUNCE`. Without one there is no wake word
  picker in HA and the satellite never returns to `idle`.

  So the box downloads and decodes every reply whatever the routing says, and
  `External player` currently means "the external speaker also gets it", not
  "the box leaves it alone". See the header of `base/core.yaml`.
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

- **The face engine wrote a width nobody had changed, every tick, for the whole
  of every answer.** `face_eyes`, `face_pupils` and `face_mouth` tested width and
  height together and then set both. The phases that actually run per tick move
  one of them: listening pulses eye height against a compile-time width, and
  replying - the longest phase there is - changes only the mouth height. Each
  `lv_obj_set_width` marks the object dirty and invalidates its old and new area,
  so this was pure loss 8.3 times a second. Tested separately now. Affects all ten
  artwork characters, which is most installs.
- **`rain` built twelve strings a tick and threw most of them away.** A column's
  text is a pure function of the phase, its `lead`, the band row and `churn`; with
  those unchanged the result is identical byte for byte, and `rain_draw` compared
  it and discarded it. That was roughly 120 heap allocations a second next to the
  audio pipeline, worst in listening where `frozen` pins the drift so nothing moves
  at all. Now skipped when the inputs match. `churn` also moved out of the row
  loop, where it was recomputed 144 times a tick to produce one number.
- **`scope` recomputed constants every frame.** Three of them, all depending only
  on the point index: the `k/(N-1)*2pi` both branches rebuilt under different
  names, the left-to-right spacing, and the entire vertical half of the thinking
  figure - which contains no frame counter at all, so it was 33 `sinf` calls a tick
  arriving at the same numbers. Pulled into tables beside the `ENV` one that was
  already there, filled once. About 66 float divisions and 33 `sinf` per tick gone.
- **`crt` drew its scanlines on top of the text.** LVGL paints in list order and
  the thirty lines were appended after the body label, seventeen of them crossing
  it, so every text change repainted all seventeen over the top. They now sit
  underneath, placed by an explicit `__SCANLINES__` marker in the generator rather
  than by which string happened to be concatenated last. They are barely above the
  background colour, so it looks the same.

- **The timer countdown was rewritten sixty times a minute to show the same
  string.** Above an hour the label reads `HH:MM`, so it changes once a minute,
  but the tick runs every second - and `lvgl.label.update` never compares, so
  each of the other fifty-nine did a `snprintf`, a `std::string`, a `strdup`
  inside LVGL and a re-layout of a 26 px font to arrive at identical pixels. The
  bar beside it already had exactly this guard; the label had been missed. The
  key compares what is *shown* (`left / 60` above an hour), not `seconds_left`.
- **`nixie` repainted its whole display on most idle ticks.** Its idle breath was
  a smooth sine, so every lit segment changed together roughly 57% of the time -
  about 140 LVGL writes a second in the state the device sits in almost
  permanently. Quantised to steps of 8, exactly as `pixel` already did with the
  comment explaining why, which lands as under 2% of brightness on screen and
  cuts it to about 27 writes a second.
- **`scope` re-pushed its trace every tick even when the shape was identical.**
  One write, but the most expensive one in the character set: it dirties the
  whole trace bounding box, over two passes of the draw buffer. While muted the
  trace is a flat constant and was being re-sent ten times a second forever. Now
  guarded by a point comparison, the same way the `vu` needles already were.

- **The box went deaf after every reply.** `start_wake_word` refused to run
  while a pipeline was still going and then silently did nothing. `on_end` holds
  the replying phase while the assistant is still in `STREAMING_RESPONSE`, so it
  called the script about two seconds before the pipeline went idle, the guard
  was false, and nothing tried again. It now waits for the pipeline and the
  speaker instead, with a timeout so a stuck state cannot hang it.
- **Two windows where the wake word started underneath the microphone.**
  Between stopping the wake word and starting the pipeline - the wake beep in
  one path, a 100 ms gap in the button path - nothing is running and the speaker
  is silent, so anything watching for "idle" started listening a fraction of a
  second before the pipeline opened the microphone. That is the flood of "Not
  enough free bytes in ring buffer". Both paths now mark the window.
- **The idle clock appeared while the box was still speaking.** The wait for
  local playback gave up after twenty seconds, which is shorter than a long
  reply, and the phase was reset the moment it expired.
- **The reply hold was measured from the wrong moment.** It estimates how long
  the answer takes to speak, but counted from after local playback had already
  finished - so in "Both" it was added on top, roughly doubling the silence.
- **A stray touch could start the assistant.** The screen reports the occasional
  touch nobody made; sixteen pipelines started this way in ten minutes, all but
  two ending in "no text recognized", each holding the microphone for about
  fifteen seconds. The button is now debounced.
- **"Diag: only the alexa model" left two models running**, having been written
  when there were two. A diagnostic that misreports its own state cannot answer
  the question it exists for.
- **Several widgets were repainted with values that had not changed** - the
  timer bar every second, the face's colour on every expression change, the
  home clock on every clock resync, and the scope trace ten times a second
  across a 284x172 px widget. `lvgl.*.update` never compares.
- **Constants were recomputed every frame**: the scope's edge envelope (33
  `sinf` plus 33 `powf` per tick) and pixel's ripple distances (96 square roots
  per tick), both fixed by geometry.
- **`aura`, `kitt` and `scope` never wrapped their frame counters**, while every
  other character did. `aura` matters most - it is the default, and feeds the
  counter straight into `sinf`.
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

- **The `jarvis` character**, along with its generator and demo clip. It was the
  most expensive face in the set and the one that made the HUD visibly crawl -
  the comment in `aura.yaml` explaining why that file writes through
  `lv_obj_set_*` instead of `lvgl.widget.update` was written about jarvis. The
  three wake words are untouched: **"hey jarvis" still works**, it is a
  `micro_wake_word` model and has nothing to do with the character.

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

- **Performance instrumentation**, all `disabled_by_default` so it costs nothing
  until you switch it on in Home Assistant: `loop_time`, free heap, largest free
  block and free PSRAM. The reason it exists: the only signal this project had
  for "the device is struggling" was the log line `lvgl took a long time for an
  operation`, which says *that* it happened but not how long or how often. With
  `loop_time` on, "is this faster" stops being a judgement call about the code
  and becomes a number. Largest-free-block sits next to free-heap deliberately -
  a fragmented heap can have plenty free and still refuse a decoder buffer, and
  free-heap alone will not show it.
- **`scripts/flash.py`**: compiles, then reads the SSID back out of the generated
  `main.cpp` and refuses to upload if it looks like a placeholder. Checking the
  config dump no longer works for this - since 2026.7.1 it prints
  `ssid: !secret '...'` rather than the value - and a placeholder SSID takes the
  device off the network and needs someone physically at it to recover.
- Tap-to-talk: a tap anywhere on the idle page, or on the GT911 "home" button
  under the screen, starts a pipeline without a wake word.
- Tapping the timer-ringing screen silences it.
- `time: platform: homeassistant`, as groundwork for anything clock-driven.
- `docs/HARDWARE.md`, `scripts/validate.py`, `scripts/esplog.py` and a Claude
  Code skill.
- **A watchdog for a deaf device.** If the assistant is idle and the wake word
  simply is not running, after 40 seconds it is started again, whatever the
  reason. It deliberately consults none of our own flags, since those are what
  get stuck. Covers the on-device engine only; the comment says so.
- **`scripts/gen/`, and the seven character files that come out of it.**
  `crt`, `kitt`, `nixie`, `pixel`, `rain`, `scope` and `vu` are
  generated - they are mostly hundreds of near-identical widget definitions. The
  scripts used to live outside the repo, which meant nobody else could run them
  and one of them had already drifted out of step with the file it writes.
- **`scripts/check_generated.py`**, which regenerates all seven, compares,
  restores whatever it touched, and fails if a file and its generator disagree.
- **`scripts/validate.py` now rejects a `wait_until` with no `timeout`.** This
  is the most expensive mistake made here: such a wait does not fail and does
  not warn, it stops that automation forever, and everything after it.
- **Swipe navigation around the idle screen.** Home sits in the middle of a
  cross; `idle_page_above` / `idle_page_below` / `idle_page_side` name the screens
  a swipe reveals, and left at their `page_status` default a swipe does nothing,
  so it is opt-in one direction at a time. Vertical is one level deep, horizontal
  wraps. A conversation still takes the screen and hands it back to whichever one
  you were reading. `swipe_min_px` is tuned to 28 px because LVGL's 50 px default
  - a sixth of the screen - dropped deliberate swipes on hardware. The gesture
  reaches the page through a full-screen button carrying `gesture_bubble`; without
  it LVGL delivers the swipe to the button that was pressed and the page never
  sees it.
- **A settings screen** (`base/screens/settings.yaml`), the device's own switches
  as tap tiles - microphone mute, wake sound and the screen, plus the `TTS output`
  toggle and a volume slider. Wired one swipe down from home in the example config
  (`idle_page_above: page_settings`). On and off differ in shape rather than only
  colour, so it reads at a glance; only the six Material Design glyphs it uses are
  compiled in. Deliberately not on it: `Speaker enable` (hardware, and the
  External-player mute already drives the amplifier), the list choices and the
  diagnostics.
- **A live `Mic gain` control.** The ES7210's hardware gain in dB, as a Home
  Assistant `number` restored across reboots and re-applied at boot. It sits
  before the split that feeds the wake word and the speech-to-text both, so it is
  the real microphone-sensitivity knob where `mww_gain_factor` only touches the
  wake word. Defaults to the chip's 24 dB, so nothing changes until you move it;
  drop it if the mic is too hot, and raise `mww_gain_factor` afterwards if the
  wake word then wants shouting at.
