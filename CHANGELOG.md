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

- **Every boot downloaded and decoded a cover for a player that was not
  playing.** Home Assistant hands out `entity_picture` whatever the state, so a
  box starting up next to a stopped speaker fetched the last track's artwork
  from hours ago: 113 KB of JPEG, **1.7 seconds of blocked loop** and six
  `Not enough free bytes in ring buffer` warnings from the wake word, for a
  picture the screen then hid behind "Nothing playing". The fetch now waits for
  the player to be playing, paused or buffering, and does not record the URL as
  seen when it skips - so pressing play fetches it normally. Measured on
  hardware: loop time max at boot fell from **1738 ms to 89 ms**, and the wake
  word warnings are gone.

- **A cover that failed to download was never retried.** The fetch guard records
  a picture as "seen" before asking for it, so one failed download - Home
  Assistant restarting, a blip - meant the note stayed until the track changed:
  every later republish of the same `entity_picture` bounced off the guard. The
  error handler now forgets the URL, so the next republish tries again.

- **The cover of the last track stayed on screen after playback stopped.** Only
  the download callbacks ever showed or hid it, so the album art sat under
  "Nothing playing" until something else was played. It now follows the player's
  state, which also makes `media_cover_ready` - written twice and read nowhere -
  mean something.

- **Cover art never arrived from Music Assistant, and the reason was a doubled
  address.** The screen prefixes `media_ha_base_url` to the player's
  `entity_picture`, which is what integrations that hand out a path need. Music
  Assistant hands out a whole URL on its own image proxy port, so the result read
  `http://host:8123http://host:8095/...` and ESP-IDF answered `Error parse url` -
  the picture, the format and the network were all fine and none of them were the
  problem. An absolute URL is now used as it stands.

- **On the media screen the title climbed onto the artist.** `long_mode: DOT` is
  not "cut at one line": it wraps first and dots whichever line runs out of room,
  and a label left to size itself grows downwards to fit. The rows are 24 px
  apart and a wrapped 16 px title wants about 40. Both labels are now pinned to a
  single row, which puts the ellipsis back on line one.

- **The progress bar opened full and frozen on the first track after a gap.** The
  position was advanced by a local clock started when Home Assistant last
  mentioned a position - and that clock kept running through pauses and idle
  time, so a quiet hour was added to the position as though it had been played,
  and the clamp pinned the bar to the right edge. Pausing appeared to fix it only
  because it made Home Assistant restate the true position. The clock now runs
  only while the state is `playing`, a position update anchors it only when
  playing, and a change of title resets it for the new track.

- **All seven generated characters had drifted from their generators, and
  `check_generated.py` could not see it.** The checker compared bytes, and the
  generators write `\n` while a Windows checkout with `core.autocrlf=true` holds
  `\r\n` - so it reported all seven as drifted on every run, everywhere, which is
  indistinguishable from reporting nothing. Behind that noise sat a real one:
  `skip: true` on `page_face` was added to the seven files by hand when the
  carousel landed and never to the generators. Running any of them would have put
  the character's page back into the swipe ring with no diff to explain it -
  precisely the failure that script exists to catch. Both fixed: the comparison
  normalises line endings, and the generators emit the line.

- **`base/assets/characters.png` had four characters drawn with the wrong face.**
  The renderer that produces it reads each character's substitutions out of its
  YAML, and it treated a comment in column 0 as the end of the substitutions
  block. `franky`, `genie`, `momo` and `wizard` all carry one in the middle of
  theirs, so those four rows were drawn with the engine's defaults - which are
  pip's numbers - rather than their own. Regenerated. The same bug was in the
  picker's generator and was fixed before it shipped a table.

  The checker also mistook a generator's INPUT for its output. It collected every
  `"*.yaml"` literal in `scripts/gen/*.py`; `gen_picker.py` reads
  `base/screens/face.yaml`, so the checker went looking for it in `base/faces/`
  and crashed. It now only counts literals on a line that assigns `OUT` or opens
  a file for writing.

- **Mute now only mutes the microphone.** It used to drive the screen too: the
  muted phase pinned you to the character's muted face, and the tap-to-swap was
  gated to the idle phase, so while muted you could not tap back to the clock. Now
  the switch does one thing - mute the mic, which also stops the wake word from
  hearing - and leaves the screen alone. The only "it is muted" indicator is the
  switch itself and its settings tile.
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

- **A thermostat screen** (`base/screens/climate.yaml`): the target temperature
  large, the room's own under it, a flame that lights only while `hvac_action`
  is actually `heating`, two arrows and a row of mode buttons.

  It needs nothing set up in Home Assistant. The step, the limits and the list
  of modes are attributes, so `min_temp`, `max_temp`, `target_temp_step` and
  `hvac_modes` are read rather than configured: the row draws three buttons for
  a TRV and six for an air conditioner that also offers cool, dry and fan_only,
  hides the rest and centres what is left. The buttons are slots - which mode
  each one commands is decided at runtime - and a mode outside Home Assistant's
  vocabulary still gets one, labelled with its raw name, because a mode we
  cannot spell is still one the device will accept.

  **Taps are optimistic and that is deliberate.** The number moves immediately
  and Home Assistant is called afterwards. A round trip takes the better part of
  a second and a thermostat is tapped in bursts, so a screen that only drew what
  came back would drop two taps in three. The local value stands for three
  seconds and is then handed back to whatever Home Assistant reports, which is
  also what corrects it when a call fails or somebody moves the same dial from
  their phone. Values are snapped to the device's own step grid, so an odd
  starting point like 20.3 walks 20.5 and 21.0 rather than 20.8.

  Cost: 23 KB, taking the author's build to 33.8% of flash.

- **A weather screen** (`base/screens/weather.yaml`), another carousel screen:
  current conditions large - icon, temperature, humidity, wind - over a row of up
  to seven days with their own icons and high/low.

  Current conditions need nothing but a `weather` entity. The forecast needs a
  helper in Home Assistant and there is no way around that: since 2024.4 a
  forecast lives only in the response to `weather.get_forecasts`, and an ESPHome
  device can call a service but cannot read what it returns. So the screen
  subscribes to one compact string a template sensor produces -
  `condition,high,low,Day|...` - which is one subscription rather than the
  twenty-one an attribute-per-field helper would need, and fits Home Assistant's
  255-character state limit for seven days with room to spare. The header of the
  package carries a template that produces it.

  **The day count is read, not configured.** met.no returns six, others five or
  ten; the screen draws a column per entry it is given, hides the rest and
  centres what is left, so nothing needs touching when the number changes
  overnight. Five days left-aligned in a seven-day row read as two columns that
  failed to draw.

  All fifteen of Home Assistant's conditions are mapped to Material Design
  icons whose codepoints were checked against the webfont's own table AND
  rendered before being written down - an unverified glyph does not fail a
  build, it draws nothing, and that only shows up on the panel. Anything
  unrecognised falls through to the alert icon rather than to an empty box.
  Cost: 47 KB of flash for both icon sizes and the large temperature font,
  taking the author's build to 33.5%.

- **One glyph less in the media screen's font.** `volume-medium` was compiled in
  and never drawn: the volume is written as text. An unused glyph does not fail
  a build, it just quietly costs flash.

- **`morgana`**, a witch, taking the cast to 29. Her artwork arrived with no eyes
  and no mouth already, so nothing had to be erased - but the two dark marks over
  her forehead are BROWS, not the closed eyes they look like at a glance. Read as
  eyes they would have put the whole face up on the forehead; read as brows they
  set the eye spacing and act for free, the way nyx's and mandrake's do.

  Her mouth is the one number here that is a decision rather than a measurement,
  and the file says so: nothing is drawn below her eyes except the blush, so the
  mouth sits on the line between the two blush marks. The ratio that placed
  earlier faces would have put it 9 px lower, on the chin. Her eyes are also
  deliberately larger than the measurement gives - chibi artwork carries its
  expression in the eye, and the measured size read as beady against cheeks that
  size.

- **The room's speaker is named once.** `media_entity` used to be a separate
  setting with an unrelated default, so a box with one external speaker named it
  twice and a box with none had nowhere to say so. The media screen now follows
  `external_media_player_id`, whose default becomes `media_player.none` - an
  entity that exists nowhere, meaning there is no such speaker. Replies stay on
  the box, the screen reports nothing playing, and the common case needs no
  configuration at all. Both stay overridable where they genuinely differ, which
  is what a Music Assistant setup wants: TTS to the Cast entity, the screen to
  the Music Assistant one.

  The sentinel is spelled like an entity because it has to be - the
  `homeassistant` text sensor rejects anything without exactly one dot, so a
  plain `none` fails validation rather than degrading quietly.

- **A rendered screenshot of the media screen** in the README
  (`base/assets/media.png`), drawn by `scripts/gen_media.py` from the screen's own
  coordinates, colours and fonts rather than photographed, so it can be redrawn
  after a layout change instead of going stale.

- **A live "Assistant" selector** (`base/faces/picker.yaml`) - a Home Assistant
  `select` that swaps the character at runtime, artwork, geometry and colours
  together, choice restored across a reboot. Four characters, named at compile
  time, because a character's PNG is 320x240 RGB565 = 150 KB of flash whether or
  not it is ever shown; which four is the compile-time decision, switching
  between them is not.

  What it cost inside the engine: **the geometry moved out of compile-time
  substitutions into runtime globals** (`fg_*` in `base/screens/face.yaml`). A
  character package still only sets substitutions - they are now the *initial
  values* of those globals rather than constants pasted into every lambda - so a
  config that names one assistant and never installs the picker is unchanged.
  Three details that would each have left the face half swapped: the primitives'
  "what did I last write" caches were function-local statics and had to become
  globals the swap can invalidate, or the first tick after a change compares the
  new numbers against the old ones and decides nothing moved; the listening
  pulse table was a `static const` array initialised from the pulse value, which
  would have frozen the first character's number in for the life of the boot;
  and the tick only ever writes x, never y, so the vertical positions are
  written by the swap itself.

  The picker is generated by `scripts/gen/gen_picker.py` from the character
  files, which stay the source of truth - it carries a table of all 14 artwork
  characters' numbers, and a hand-copied table would drift the first time
  somebody nudged an eye.

- **Cover art on the media screen, and buttons that admit what they cannot do.**
  The device downloads the picture from Home Assistant's own image proxy and
  decodes it on board as JPEG, which needs a new `media_ha_base_url` - the
  player's `entity_picture` is a path, and the base has to be an address the BOX
  can reach, not the one your laptop uses. Same URL twice in a row is not
  fetched twice: Home Assistant republishes the attribute on every state event,
  and the download is the one genuinely expensive thing this screen does.

  Previous and next now follow the player's `supported_features`. A Chromecast
  casting from some apps advertises pause and nothing else, and Home Assistant
  answers the call with `ServiceNotSupported` - which from the sofa is
  indistinguishable from a broken screen. Unsupported buttons are painted dim
  and do nothing when tapped. Cost of both: 39 KB of flash, to 32.9%.

- **`vesta`**, taking the cast to 28. Her artwork kept the eye SHADOW as well
  as the brows and the nose, and that shadow is what places the eyes: it is
  where they were, so it beats any proportion of a face in general. Her face
  also sits right of frame centre, which is what `face_center_x` is for.
- **Two more characters** - `willow` and `nyx` - taking the cast to 27. Both are
  emblem-style vector art with the face taken out, and both were measured rather
  than guessed, which took three attempts to learn. What settles a placement is
  never the proportions of a face in general; it is the landmarks the artwork
  still has. Willow's mask carries a nose and nothing else, so the nose is the
  scale check: if the measured eye line puts it where it is drawn, the scale is
  right. Nyx kept her eyebrows, and their centres are what sets the eye spacing.

  Willow's eyes are then deliberately bigger than the measurement says. The
  numbers off the original produce eyes that read as beady at this size, and the
  file says so, so that nobody later "fixes" them back to the measured value.

- **Four more characters** - `kacpro`, `hacker`, `mandrake` and `spike` - taking
  the cast to 25. Two of them cost nothing but measurement: KacPRO's hood and
  hacker's blank oval arrived with the face area already empty. Mandrake did not.
  It came asleep, with closed-eye arcs and lips painted straight onto an orange
  gradient, and rhea's trick of keeping them as eyebrows does not work when the
  arcs sit where the eyes go. They were grown back over from the surrounding
  pixels instead of filled flat, which on a gradient would have read as a patch;
  the two leaves above them were kept and do the eyebrow job. Spike had two dark
  specks exactly where its mouth belongs, painted out the same way. Mandrake is
  also the tightest face in the set at 21 px of clean bulb, so its mouth opens by
  9 px where pip's opens by 22 - every expression dimension being a substitution
  is what makes that possible without touching the engine.
- **`base/assets/characters.png` regenerated**, and it is no longer three
  characters out of date: one row per character with artwork, fourteen of them
  now, across the same five phases.
- **A live "Home style" selector** (`base/screens/home-styles.yaml`) - a Home
  Assistant `select` that restyles the home screen at runtime, no rebuild, choice
  restored across a reboot. 40 looks: palettes and fonts (CRT, Neon, Minecraft,
  Vaporwave, Amber, Minimal, Bold, Glitch, Pixel, Stencil, Racer, Zen, Cyber,
  Mono), layouts (Big, Terminal, Stack, RightCol, Corner), a temperature /
  humidity **Dashboard** with icons, vertical and horizontal gradients (Sunset,
  Ocean, Aurora, Synthwave, Forest, Fire, Ice, Sunrise, Tide) and light themes
  (Paper, Blueprint). `home.yaml` is parameterised so the Default look is unchanged
  and any value can also be pinned at compile time; each clock font is a Google
  Font compiled as digits and a colon only, so the whole set is a few KB. Only the
  home screen is touched.
- **A "Station" family, eight more Home styles** riding on the same selector: the
  same three sensors as Dashboard's small icon row, redrawn big enough to read
  from across the kitchen - a big outdoor reading over a divider, a small indoor
  temperature/humidity strip below it. `Station`, `Station Neon`, `Station Amber`,
  `Station Fire`, `Station Ice`, `Station Forest` and `Station Paper` each borrow
  their palette from the matching style already in the list, so nothing new was
  invented; `Station Aura` matches the `aura` character instead, right down to
  its divider, which freezes one frame of the same idle line `aura.yaml` breathes
  on the character screen. Reuses Dashboard's three widgets and its 20-second,
  visibility-gated refresh rather than adding a second set of sensors.
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
- **Swipe navigation around the idle screen.** Home has two vertical neighbours
  named by `idle_page_above` / `idle_page_below` - left at their default a swipe
  does nothing, so vertical is opt-in - and a **horizontal carousel** of home
  plus any extra idle screen packages, stepped through with a left/right swipe and
  wrapping at the ends. The carousel takes no substitution: a screen joins the
  ring by being a `skip: false` page, in `files:` order, and the core walks it
  with `lvgl.page.next` / `previous`, putting you back where you were after a
  conversation by page index. Vertical is one level deep and belongs to home;
  horizontal wraps. `swipe_min_px` is tuned to 28 px because LVGL's 50 px default
  - a sixth of the screen - dropped deliberate swipes on hardware. The gesture
  reaches the page through a full-screen button carrying `gesture_bubble`; without
  it LVGL delivers the swipe to the button that was pressed and the page never
  sees it. Adding a screen is a copy-paste: `base/screens/CAROUSEL.md` and the
  `carousel-example.yaml` beside it.
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
  wake word. Defaulted to the chip's 24 dB at the time this was written; the
  full-duplex migration below later moved the default to 12 dB. Drop it further
  if the mic is too hot, and raise `mww_gain_factor` afterwards if the wake word
  then wants shouting at.

- **Full duplex audio, with a hardware echo reference.** The stock
  `audio_adc`/`audio_dac`/`i2s_audio` layout is replaced by `esp_audio_stack` +
  `esp_aec`: mic on TDM slot 0, the box's own speaker output looped back onto
  slot 1 as a hardware echo reference, 48 kHz bus decimated to 16 kHz for the
  wake word and speech-to-text. The point of it: the microphone no longer has
  to let go of the bus for the speaker to use it, which the rest of this
  section is built on.

  Getting it onto real hardware cost two separate defects, both root-caused
  from a USB serial log rather than the network API (the first happens before
  WiFi comes up, so the API log only ever shows the aftermath). DMA-capable
  internal RAM ran out once the full core was loaded on top of it - LVGL,
  three wake word models, fonts and artwork all competing with the audio
  driver's own DMA descriptors - and took the microphone down with it after
  exactly one question, every boot; fixed by moving code, constants, TLS
  buffers and the non-DMA audio buffers into PSRAM and asking for less DMA per
  channel. And a wait in `on_end` that looked like leftover bus-arbitration
  code turned out to be the only thing keeping the talking animation synced to
  how long the reply actually takes; removed once, restored with the reason
  written down this time.

  `alexa_sliding_window` drops from 3 to 1: a 3-frame average dilutes the
  one-frame-wide detection peak that barge-in (below) needs to clear while the
  box is talking. `okay_nabu` and `hey_jarvis` stay at 3, since neither was
  part of the measurement. Hardware mic gain moves from an ES7210 register to
  a post-AEC software trim defaulting to 12 dB rather than the chip's stock
  24 (see above): measured at 1 false wake per 35 minutes in a lived-in
  kitchen against 3 at the default, with no cost to a ten-for-ten hit rate.
  `alexa_probability_cutoff` later moved from 0.6 to 0.7 and the wake-word
  model's own VAD gate was re-enabled, once the mic-gain change alone turned
  out not to be enough - one measured false wake had already scored 0.72,
  so a cutoff-only fix would have needed 0.75 and cost three of ten real
  words.

  This also lifts the bus-sharing constraint noted above for the wake sound:
  mic and speaker no longer fight over one I2S bus, so the beep no longer has
  to finish before the assistant can listen. The sound itself was not
  lengthened; 180 ms already works.

- **Barge-in: saying the wake word interrupts a reply mid-sentence**, on the
  box's own speaker and on an external one. Two separate stock-ESPHome
  behaviours had to be worked around, both found by testing the real thing
  rather than trusting a Home Assistant history timestamp that looked like
  evidence but was not. `on_wake_word_detected` calling `voice_assistant.start:`
  is `request_start()`, which silently does nothing unless the component is
  already `IDLE` - so a wake word heard mid-reply used to do nothing at all,
  even once it was confirmed the wake word itself was heard fine. And
  `micro_wake_word` turns itself off the instant a pipeline leaves `IDLE` and
  only comes back once the whole reply has finished, so there was no listener
  present during a reply regardless of the first fix. Fixed by explicitly
  restarting the wake word in `on_tts_start` and having
  `on_wake_word_detected` stop the running reply and wait for `IDLE` before
  starting the next one.

  For a reply routed to an external speaker, the stop now reaches it too: the
  audible copy there is a separate `media_player.play_media` call to Home
  Assistant, untouched by the box's own state, so it needed its own explicit
  `media_player.media_stop`.

  Confirmed on hardware, mic and speaker running at once for the first time on
  this board (`Runtime state: duplex` in the log): a mid-reply "Alexa" at
  0.72-0.99 cuts the reply within about 90 ms and a new listen starts cleanly,
  repeatedly, with no sign of the DMA/RAM exhaustion this board hit during the
  migration itself.

- **A ringing timer can be silenced by saying the wake word**, not just by
  touch. `micro_wake_word` never stops for a ringing timer - it does not touch
  `voice_assistant` state at all - so "Alexa" is heard immediately. The first
  attempt on hardware left the wake-confirmation beep looping every 1.4
  seconds instead: silencing only the current sound left the timer's own
  "repeat until silenced" setting armed on the media player, and the beep
  that played next inherited it. Fixed by having a detected wake word turn the
  `Timer ringing` switch off directly, reusing the cleanup that switch already
  does correctly for a touch or a Home Assistant automation.
