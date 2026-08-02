![ESPHome and Home Assistant voice assistant on the ESP32-S3-BOX-3](docs/hero.jpg)

# ESPHome Voice Assistant for the ESP32-S3-BOX-3

A **Home Assistant voice satellite** for the
[ESP32-S3-BOX-3](https://github.com/espressif/esp-box), built on **LVGL and the
touchscreen** instead of the static full-screen images the stock config paints.
Pure ESPHome, no custom C firmware: an always-on core you pull as a package, plus
one thin config file you actually edit.

> **Status: running on an ESP32-S3-BOX-3.** Wake word, the full Assist pipeline,
> full duplex audio with barge-in, voice timers with their alarm, the
> touchscreen, the animated character, the home, settings, media, weather and
> thermostat screens are all confirmed on device with ESPHome 2026.7.1. The
> shipped thin config - core plus one character - measures **flash 27.0%, RAM
> 41.3%**, up from 25.3%/39.9% before the full-duplex migration; the
> four-characters-plus-every-optional-screen figure predates that migration
> and has not been remeasured yet. Artwork is what costs: 150 KB per
> character. [CHANGELOG.md](CHANGELOG.md) has the detail, including what
> turned out to be wrong along the way.

> [!TIP]
> ⭐ **Enjoying this project?** Every star is real motivation for me to keep
> developing it :)

## What it does

- **Voice assistant**: on-device wake word (`alexa`, `okay nabu`, `hey jarvis`,
  pick one in Home Assistant) via
  `micro_wake_word`, the full Home Assistant Assist pipeline (STT / LLM / TTS),
  and a mic that mutes from HA.
- **Full duplex, with a hardware echo reference**: the mic never has to let go
  of the bus for the speaker to use it. Practical effect: say the wake word
  again while a reply is still playing and it cuts the reply short and starts
  listening, on the box's own speaker or an external one; a ringing timer can
  be silenced the same way, not just by touch.
- **LVGL UI**: a page per assistant phase, claimed by whichever screen package
  you install. With none, the core shows plain text status screens; that is the
  floor, not the intended look.
- **Touchscreen**: the GT911 is wired into LVGL. The **button under the screen**
  (which is not a GPIO - it is GT911 touch button 0) starts the assistant, and
  silences a ringing timer instead if one is going. **Tapping the screen while
  idle swaps between the clock and the character**, and back; the choice survives
  a reboot. **Swiping the idle screen** moves to a neighbouring screen - a
  settings page one swipe down, by default. Starting the assistant is left to the
  button so that screen taps belong to the UI rather than fighting a full-screen
  tap-to-talk target.
- **Timers**: set by voice, with a countdown and a progress strip on LVGL's top
  layer that stays visible across page changes (green while running, blue while
  paused).
- **TTS routing you choose at runtime**: the reply can come out of the box, out
  of a Home Assistant media player elsewhere in the house, or both. Details:
  [TTS routing](https://github.com/MichalZaniewicz/esphome-esp32-s3-box-3-va/wiki/TTS-routing).
- **Swappable assistant**: the on-screen character is a package - artwork plus
  the measurements of where its face goes - so changing assistants is one line.
- **🔥 Draw on screen**: Home Assistant can make the box draw whatever it wants
  on the touchscreen, on demand - "Alexa, draw a sun" - rectangles,
  circles, text and Material Design icons, on a blank page it switches to on
  its own and dismisses with a tap or swipe. Only reachable from Home
  Assistant, never a button or swipe on the box itself. [Details
  below](#draw-on-screen).

## Characters

Swapping the assistant is one word. Each character in
[`base/faces/`](base/faces/README.md) pulls whatever it needs by itself, so
nothing else in the config changes:

```yaml
substitutions:
  assistant: pip     # <- the only line that picks a character

packages:
  core:
    files:
      - base/core.yaml
      - base/faces/${assistant}.yaml
```

Whichever one you name, it exposes the same page id, `page_face`, so
`idle_page_alt: page_face` keeps working across a swap.

**Or switch without a rebuild.** Add `base/faces/picker.yaml` and name three more
characters; an **Assistant** select appears in Home Assistant and changes the
artwork, the geometry and the colours on the spot, choice restored after a
reboot. Four rather than all of them because each character's PNG is 150 KB of
flash compiled in whether or not it is ever shown - which four is a compile-time
decision, switching between them is not. Artwork characters only. Details:
[`base/faces/README.md`](base/faces/README.md#switching-one-while-it-runs).

### The cast

Twenty-eight of them, and they are not one face on twenty-eight bodies: the
eyes, the colours, the range of every expression and in ten cases the entire way of
being on screen belong to the character. Name any of them in lower case.

<table>
  <tr>
    <td width="290"><img src="base/assets/demo/demo-aura.gif" width="272" alt="Aura"></td>
    <td><h3>Aura</h3>Pure voice, and entirely at peace with it. Runs a house on sentences alone, never needs telling twice, and privately thinks anyone still crossing a room to reach a switch is doing it the hard way.</td>
  </tr>
  <tr>
    <td width="290"><img src="base/assets/demo/demo-kitt.gif" width="272" alt="Kitt"></td>
    <td><h3>Kitt</h3>On duty, and has been for years. Treats a kitchen timer as an assignment and your evening routine as a patrol, and if the lights go off at eleven it is because that was the plan all along.</td>
  </tr>
  <tr>
    <td width="290"><img src="base/assets/demo/demo-crt.gif" width="272" alt="CRT"></td>
    <td><h3>CRT</h3>An old terminal that never got switched off. Prints back everything it hears and everything it answers, on the principle that a house should keep records. Runs the automation you asked for and then, in effect, files the paperwork.</td>
  </tr>
  <tr>
    <td width="290"><img src="base/assets/demo/demo-iris.gif" width="272" alt="Iris"></td>
    <td><h3>Iris</h3>Watches the room the way a sensor would if a sensor could take an interest. Knows the kettle went on, knows nobody has opened a window all day, and finds it odd that you ask what the temperature is when the thermostat is right there.</td>
  </tr>
  <tr>
    <td width="290"><img src="base/assets/demo/demo-rain.gif" width="272" alt="Rain"></td>
    <td><h3>Rain</h3>Calm to the point of being a weather system, and the only assistant here for whom "set the mood" is a literal instruction. Dims the lamps, lowers the room, and never once asks whether you are sure.</td>
  </tr>
  <tr>
    <td width="290"><img src="base/assets/demo/demo-pixel.gif" width="272" alt="Pixel"></td>
    <td><h3>Pixel</h3>A departure board that grew curious about the people reading it. Announces your timers like platform changes and finds the whole business of a house that answers back quietly thrilling.</td>
  </tr>
  <tr>
    <td width="290"><img src="base/assets/demo/demo-bit.gif" width="272" alt="Bit"></td>
    <td><h3>Bit</h3>Minimal on purpose. You asked for the lights off, the lights are off, and there is nothing further to discuss - the shortest distance between a sentence and a switch.</td>
  </tr>
  <tr>
    <td width="290"><img src="base/assets/demo/demo-rhea.gif" width="272" alt="Rhea"></td>
    <td><h3>Rhea</h3>Helping out between assignments and far too polite to say so. Sets a kitchen timer with the gravity of a rescue operation and is plainly hoping that one day you ask for something harder.</td>
  </tr>
  <tr>
    <td width="290"><img src="base/assets/demo/demo-nixie.gif" width="272" alt="Nixie"></td>
    <td><h3>Nixie</h3>Keeps the time when nobody is asking, which it regards as the real work. Humours voice control as a passing fashion and suspects your automations would manage perfectly well without the ceremony.</td>
  </tr>
  <tr>
    <td width="290"><img src="base/assets/demo/demo-scope.gif" width="272" alt="Scope"></td>
    <td><h3>Scope</h3>Reads the room in the literal sense: everything arriving is a signal, including you. Will run the scene you asked for, but is more interested in the shape of the request than in the lamp at the end of it.</td>
  </tr>
  <tr>
    <td width="290"><img src="base/assets/demo/demo-vu.gif" width="272" alt="VU"></td>
    <td><h3>VU</h3>Belongs to a hi-fi and has never got over the reassignment. Takes volume personally, treats a long reply as a performance, and considers "turn it down" the three rudest words in the house.</td>
  </tr>
  <tr>
    <td width="290"><img src="base/assets/demo/demo-rufus.gif" width="272" alt="Rufus"></td>
    <td><h3>Rufus</h3>Waiting for somebody to need saving and willing to settle for a kitchen timer. Every request is a mission, including turning on a lamp, and he will confirm when the objective is secure.</td>
  </tr>
  <tr>
    <td width="290"><img src="base/assets/demo/demo-agnes.gif" width="272" alt="Agnes"></td>
    <td><h3>Agnes</h3>Always halfway through her own day and happy to fold your request into it. Talks to you like a neighbour leaning in the doorway, and turns the lights off behind you without making a thing of it.</td>
  </tr>
  <tr>
    <td width="290"><img src="base/assets/demo/demo-pip.gif" width="272" alt="Pip"></td>
    <td><h3>Pip</h3>Earnest, easily impressed, and quietly certain he is the reason the kitchen runs at all. He is not - the automations are - but he takes the credit with such goodwill that nobody has the heart to correct him.</td>
  </tr>
  <tr>
    <td width="290"><img src="base/assets/demo/demo-astro.gif" width="272" alt="Astro"></td>
    <td><h3>Astro</h3>Has been waiting all morning for somebody to walk in and give him something to do. Receives "set a timer" as a mission briefing and regards the thermostat as life support.</td>
  </tr>
  <tr>
    <td width="290"><img src="base/assets/demo/demo-momo.gif" width="272" alt="Momo"></td>
    <td><h3>Momo</h3>A cat who woke up as a terminal and declines to discuss it. Does exactly what you asked, immediately, and explains nothing; when an automation misfires you will not be told which one.</td>
  </tr>
  <tr>
    <td width="290"><img src="base/assets/demo/demo-franky.gif" width="272" alt="Franky"></td>
    <td><h3>Franky</h3>Assembled out of spare parts and delighted with the arrangement. Considers himself living proof that a house of mismatched devices can be made to work, and would like you to know he is very good at timers.</td>
  </tr>
  <tr>
    <td width="290"><img src="base/assets/demo/demo-wizard.gif" width="272" alt="Wizard"></td>
    <td><h3>Wizard</h3>Says as little as possible and makes every word feel expensive. Switching off a lamp is beneath him. He does it anyway, and somehow leaves you feeling it was a favour.</td>
  </tr>
  <tr>
    <td width="290"><img src="base/assets/demo/demo-genie.gif" width="272" alt="Genie"></td>
    <td><h3>Genie</h3>Grants timers instead of wishes and considers this a promotion. Three of anything is the limit, on principle, though he will stretch to a fourth if asked nicely. Do not get him started on lamps.</td>
  </tr>
  <tr>
    <td width="290"><img src="base/assets/demo/demo-flare.gif" width="272" alt="Flare"></td>
    <td><h3>Flare</h3>Runs hot about everything, the thermostat included. Thinks every scene could stand to be brighter, greets a request for mood lighting as a personal challenge, and has never once suggested turning something down.</td>
  </tr>
  <tr>
    <td width="290"><img src="base/assets/demo/demo-kacpro.gif" width="272" alt="KacPRO"></td>
    <td><h3>KacPRO</h3>Answers without looking up, as though your timer is one more window among the twenty he has open. Knows exactly which automation broke and will tell you the moment he finishes what he was doing.</td>
  </tr>
  <tr>
    <td width="290"><img src="base/assets/demo/demo-hacker.gif" width="272" alt="hacker"></td>
    <td><h3>Hacker</h3>Perfectly helpful, perfectly polite, and already inside the network. Knows every device in the house by name, mentions this more often than strictly necessary, and has read your automations.</td>
  </tr>
  <tr>
    <td width="290"><img src="base/assets/demo/demo-mandrake.gif" width="272" alt="Mandrake"></td>
    <td><h3>Mandrake</h3>A root that climbed out of the pot and stayed. Slow to wake and unmoved by urgency. Your timer will happen. Plants got by for a few hundred million years without a single automation, and it sees no reason to start rushing now.</td>
  </tr>
  <tr>
    <td width="290"><img src="base/assets/demo/demo-vesta.gif" width="272" alt="Vesta"></td>
    <td><h3>Vesta</h3>Goddess of the hearth, retired into a smart home and quietly pleased with the upgrade. The thermostat answers to her now, she grants your timers rather than merely setting them, and she holds firm views on how warm a kitchen ought to be kept.</td>
  </tr>
  <tr>
    <td width="290"><img src="base/assets/demo/demo-willow.gif" width="272" alt="Willow"></td>
    <td><h3>Willow</h3>Runs the house the way a forest runs itself: slowly, and without being asked twice. Sets your timers, dims your lamps, and gently implies that the plants were managing all of this long before the wifi.</td>
  </tr>
  <tr>
    <td width="290"><img src="base/assets/demo/demo-nyx.gif" width="272" alt="Nyx"></td>
    <td><h3>Nyx</h3>Nocturnal, unimpressed, and delighted that your lights take orders. Handles the evening routine with the enthusiasm of somebody whose day starts at sunset, and treats "good night, turn everything off" as an invitation.</td>
  </tr>
  <tr>
    <td width="290"><img src="base/assets/demo/demo-spike.gif" width="272" alt="Spike"></td>
    <td><h3>Spike</h3>Needs nothing from anybody and communicates this mostly by saying nothing. Watches the kitchen constantly, speaks when asked, and regards a house that waters its own plants as the summit of civilisation.</td>
  </tr>
  <tr>
    <td width="290"><img src="base/assets/demo/demo-morgana.gif" width="272" alt="Morgana"></td>
    <td><h3>Morgana</h3>Holds that every switch in the house answers to her, and, wired into Home Assistant, she is not wrong. She waves the wand, the kitchen light comes on, and she takes the credit. A lamp that stays dark never casts doubt on the incantation, only on your wifi - and the pause before a scene runs is dramatic timing, not a round trip.</td>
  </tr>
</table>

Every clip above is generated by replaying the animation at its real tick against
that character's own numbers, read out of its YAML - so a change to a character
shows up in its clip. The characters with artwork run idle → listening →
thinking → replying, from
[`scripts/gen_demos.py`](scripts/gen_demos.py); the ones that draw themselves
skip listening where it looks the same as idle. The only edit is a couple of
seconds trimmed from the idle pause, which on the device is longer and stiller.

Ten of them need no artwork at all and draw themselves. For the rest, adding
one is `cp pip.yaml yours.yaml`, a faceless 320x240 image, and measuring where its
eyes and mouth belong. Every expression dimension is a substitution, so a bigger
or smaller face rescales without touching the engine. Details:
[`base/faces/README.md`](base/faces/README.md).

## Quick start

> Requires **ESPHome 2026.7.0+** - that is where `image:` became a platform component.

1. Copy `secrets.example.yaml` to `secrets.yaml` and fill in your Wi-Fi.
2. Copy **`esp32-s3-box-3-va.yaml`** next to it and edit the `substitutions:` at
   the top (device name, external media player, room sensors). That thin
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
5. Say "Alexa" (or "OK Nabu", or "Hey Jarvis"), or press the button under the
   screen.

After changing anything in the core, run `esphome clean` before the next build -
otherwise ESPHome reuses the cached copy of the remote package.

## Repository layout

```
esp32-s3-box-3-va.yaml     # YOUR config: copy + edit this (pulls the rest from GitHub)
secrets.example.yaml       # copy to secrets.yaml
base/
  core.yaml                # the always-on core, pulled as a remote package
  screens/
    home.yaml              # optional home screen: clock, date, climate
    face.yaml              # optional animated assistant face (the engine)
  faces/
    pip, astro, momo,      # characters; pick one with `assistant:`
    franky, wizard,        #   artwork ones pull the face engine themselves
    genie, flare, rhea,
    rufus, agnes, kacpro,
    hacker, mandrake,
    spike, willow, nyx,
    vesta, morgana
    picker.yaml            # optional: an "Assistant" select, four to switch between
    aura, bit, iris,       # these draw themselves, no artwork at all
    crt, kitt, nixie,
    pixel, rain,
    scope, vu              #   seven of these are GENERATED - see scripts/gen
  lang/
    en.yaml, pl.yaml       # UI translations; copy en.yaml to add one
  sounds/
    timer_finished.flac    # the timer alarm, compiled into the firmware
docs/
  HARDWARE.md              # pinout, I2C map, gotchas
scripts/
  validate.py              # offline YAML check: syntax, substitutions, duplicate
                           #   ids, action shape, and a wait_until with no timeout
  check_generated.py       # are the generated characters still in step with
                           #   their generators? fails if one was hand-edited
  gen/                     # the generators for crt, kitt, nixie, pixel,
                           #   rain, scope, vu - edit these, not the YAML
  gen_media.py             # redraws base/assets/media.png from the media
                           #   screen's own coordinates, colours and fonts
  gen_weather.py           # the same for base/assets/weather.png
  gen_climate.py           # the same for base/assets/climate.png
  gen_home_styles_station.py # redraws the 8 Station previews in base/assets/home-styles/
  gen_canvas_example.py    # redraws base/assets/canvas-example.png from a canvas.yaml spec
  esplog.py                # stream device logs over the native API
  flash.py                 # compile + OTA, but refuses to upload if the SSID
                           #   compiled into main.cpp looks like a placeholder
skill/
  esp32-s3-box-3/          # Claude Code skill: pinout + hard-won gotchas
```

## Configuration

Day-to-day settings are Home Assistant entities, not config edits: microphone
mute, mic gain, wake sound, screen brightness, TTS output, wake word engine
location, the wake word itself and the timer switch. **`Mic gain`** is the
ES7210's hardware gain in dB: it sits before the split that feeds the wake word
and the speech-to-text both, so it is the real microphone-sensitivity knob, and
it is restored across reboots.

Three substitutions are worth deciding before the first flash. The clock is not
among them: Home Assistant supplies the time zone along with the time.

| Substitution | Default | What it does |
|---|---|---|
| `name` / `friendly_name` | `esp32-s3-box-3-va` / `S3 Box 3 Voice` | Device name. Changing `name` re-creates every entity in Home Assistant. |
| `external_media_player_id` | `media_player.none` | The speaker this room has besides the box. Where the reply goes when `TTS output` is `External player` or `Both`, and what `media.yaml` watches unless told otherwise. The default is not a real entity: it means there is no such speaker, everything stays on the box, and nothing has to be set. |
| `tts_output_default` | `This device` | Boot default of that select. Leave it here when there is no external speaker. |

Everything else has a working default: wake word tuning, sounds, fonts, screen
pages, the boot animation, pins. All of it is in the
[Configuration reference](https://github.com/MichalZaniewicz/esphome-esp32-s3-box-3-va/wiki/Configuration)
on the wiki.

Three wake words are compiled in - **alexa**, **okay nabu** and **hey jarvis** -
and Home Assistant picks between them, one at a time.

## Screens

The core ships one page per assistant phase. Extra screens are optional packages
under `base/screens/` - add the file to your `files:` list to compile it in, drop
the line to leave it out. ESPHome merges each package's `lvgl:` block into one UI.

| Screen | What it adds |
|---|---|
| `home.yaml` | Clock, date, room temperature/humidity and outdoor temperature, in place of the core's plain text idle screen. Needs `idle_page: page_home` and your HA entity ids; day and month names are substitutions, so it localises without touching the core. |
| `face.yaml` | An animated assistant: a static character image with eyes, pupils and a mouth drawn on top as LVGL rectangles, reshaped per phase - blinking and glancing about while idle, wide-eyed listening, pupils darting while thinking, mouth moving while replying, red and shaking when a timer goes off. Claims the active phases and leaves idle alone, so it composes with `home.yaml`. Only the small widgets ever redraw, never the background. |
| `settings.yaml` | The device's own switches as tap tiles - microphone mute, wake sound and the screen, plus the `TTS output` toggle and a volume slider. Reached one swipe down from home (`idle_page_above: page_settings`). The on and off states differ in shape, not only colour, so the screen reads at a glance; the icons are the handful of Material Design glyphs actually used, downloaded at compile time. |
| `media.yaml` | What is playing on any Home Assistant media player - title, artist, a progress bar and previous / play-pause / next as tap buttons. A **carousel screen**: one swipe left or right from home. It follows `external_media_player_id` on its own, so a room with one speaker names it once; set `media_entity` only when the screen should watch something else - a TV, another room, or the box's own player, `media_player.<name>_<friendly_name>` slugified. Where Music Assistant and the Cast integration both publish a speaker, pick the Music Assistant one: the raw Cast entity offers no previous/next and no track length. The bar advances locally between Home Assistant's occasional position updates, and only while the page is on screen. |
| `weather.yaml` | Current conditions big - icon, temperature, humidity and wind - over a forecast row of up to seven days, each with its own icon and high/low. A **carousel screen**: one swipe sideways from home. Current conditions come straight from a `weather` entity; the forecast needs a small helper in Home Assistant, because since 2024.4 a forecast lives only in a service response and a device cannot read one. The screen draws a column per day it is given and centres them, so a five-day integration and a ten-day one both look deliberate. |
| `climate.yaml` | A thermostat: the target temperature large, the room's own below it, a flame that lights only while the device is actually heating, two arrows and a row of mode buttons. A **carousel screen**: one swipe sideways from home. Needs nothing in Home Assistant - the step, the limits and the list of modes are all attributes, so the row has three buttons on a TRV and six on an air conditioner without being told. Taps move the number at once and call Home Assistant after, because a thermostat is tapped in bursts. |
| `home-styles.yaml` | A live **"Home style"** selector in Home Assistant - 40 looks for the home screen (fonts, colours, gradient backgrounds, layouts, a temperature/humidity dashboard, and a big-outdoor-reading "Station" family in eight palettes) switched at runtime with no rebuild, the choice restored across a reboot. Rides on `home.yaml` and touches only the home screen. See [Home styles](#home-styles) below. |
| `show-screen.yaml` | Four Home Assistant buttons - **"Show home/weather/thermostat/media screen"** - that jump the display to whichever one is pressed, meant for Assist ("Alexa, pokaż pogodę"). Needs `home.yaml`, `weather.yaml`, `climate.yaml` and `media.yaml` all installed, since it has to name each one's page directly. See [Voice control](#voice-control) below. |
| `canvas.yaml` | Lets Assist **draw whatever it wants on the screen** - "Alexa, draw a sun" - rectangles, circles, text and Material Design icons, on a blank page it switches to on its own. Only reachable from Home Assistant: never a swipe, never a button on the Box. Needs nothing else. See [Voice control](#voice-control) below. |

The **settings screen** is **one swipe down** from home - the device's own switches
as tap tiles (microphone, wake sound, and where replies come out) plus a volume
slider, each state told by shape and colour so it reads at a glance:

<p align="center"><img src="base/assets/settings.png" width="300" alt="Settings screen"></p>

The **media screen** is **one swipe sideways** from home - cover art fetched and
decoded on the device, title and artist on one line each, a progress bar that
advances between Home Assistant's occasional updates, and three controls that dim
themselves when the player does not support them:

<p align="center"><img src="base/assets/media.png" width="300" alt="Media screen"></p>

The **weather screen** is another carousel screen: what it is doing now, over
what it will do for the rest of the week. The forecast row needs a helper in
Home Assistant - the header of
[`base/screens/weather.yaml`](base/screens/weather.yaml) has a template that
produces it in a dozen lines - and without one the current conditions work on
their own:

<p align="center"><img src="base/assets/weather.png" width="300" alt="Weather screen"></p>

The **thermostat screen** is the third of them, and the only one you can argue
with. Two arrows, a row of modes built from whatever the device says it has, and
a flame that lights when it is genuinely heating rather than merely willing to:

<p align="center"><img src="base/assets/climate.png" width="300" alt="Thermostat screen"></p>

Install both `home.yaml` and `face.yaml` and the idle screen has two faces: the
clock, and the character idling. **Tap the screen to swap between them** -
`idle_page` is what you see after a reboot, `idle_page_alt` is what a tap
switches to, and the last choice is remembered. Set them to the same page to turn
the tap off.

```yaml
  idle_page: page_home      # clock, date, temperatures
  idle_page_alt: page_face  # the character, blinking and looking around
```

### Swipe navigation

Home has two vertical neighbours and a horizontal carousel. The **vertical** ones
are named by substitution and are opt-in - left at their default a swipe does
nothing:

```yaml
  idle_page_above: page_settings  # swipe DOWN brings it in from the top
  idle_page_below: page_status    # swipe UP; unset here, so up does nothing
```

The **horizontal** axis is a carousel: home plus any extra idle screen packages
you install, stepped through with a left or right swipe and wrapping at the ends.
There is no substitution for it - a screen joins the ring by being installed, in
the order you list it under `files:`, and home is always first. Adding one is a
copy-paste: see [base/screens/CAROUSEL.md](base/screens/CAROUSEL.md) and the
[carousel-example.yaml](base/screens/carousel-example.yaml) beside it.

Vertical is one level deep, does not loop, and belongs to home; horizontal wraps.
A conversation takes the screen as it always has and hands it back to whichever
one you were reading when it finishes. Swipe sensitivity is a substitution
(`swipe_min_px`), tuned down from LVGL's default because a sixth of the screen was
dropping deliberate swipes.

### Home styles

Add `base/screens/home-styles.yaml` after `home.yaml` and a **"Home style"**
select appears in Home Assistant. Pick a look and the clock font, the colours, the
background and the layout change live - no rebuild - and the choice survives a
reboot. Only the home screen is restyled; nothing else moves.

```yaml
  files:
    - base/core.yaml
    - base/screens/home.yaml
    - base/screens/home-styles.yaml   # the selector
```

The 40 styles, at the device's native 320x240 - layouts (Default, Big, Terminal,
Stack, **Dashboard** with temperature/humidity icons, RightCol, Corner, **Station**
with a big outdoor reading over a small indoor strip), fonts and palettes,
vertical and horizontal gradient backgrounds, and light themes:

<table>
<tr>
<td align="center"><img src="base/assets/home-styles/default.png" width="200"><br><sub><b>Default</b></sub></td>
<td align="center"><img src="base/assets/home-styles/big.png" width="200"><br><sub><b>Big</b></sub></td>
<td align="center"><img src="base/assets/home-styles/terminal.png" width="200"><br><sub><b>Terminal</b></sub></td>
<td align="center"><img src="base/assets/home-styles/stack.png" width="200"><br><sub><b>Stack</b></sub></td>
</tr>
<tr>
<td align="center"><img src="base/assets/home-styles/dashboard.png" width="200"><br><sub><b>Dashboard</b></sub></td>
<td align="center"><img src="base/assets/home-styles/rightcol.png" width="200"><br><sub><b>RightCol</b></sub></td>
<td align="center"><img src="base/assets/home-styles/corner.png" width="200"><br><sub><b>Corner</b></sub></td>
<td align="center"><img src="base/assets/home-styles/crt.png" width="200"><br><sub><b>CRT</b></sub></td>
</tr>
<tr>
<td align="center"><img src="base/assets/home-styles/neon.png" width="200"><br><sub><b>Neon</b></sub></td>
<td align="center"><img src="base/assets/home-styles/minecraft.png" width="200"><br><sub><b>Minecraft</b></sub></td>
<td align="center"><img src="base/assets/home-styles/vaporwave.png" width="200"><br><sub><b>Vaporwave</b></sub></td>
<td align="center"><img src="base/assets/home-styles/amber.png" width="200"><br><sub><b>Amber</b></sub></td>
</tr>
<tr>
<td align="center"><img src="base/assets/home-styles/minimal.png" width="200"><br><sub><b>Minimal</b></sub></td>
<td align="center"><img src="base/assets/home-styles/bold.png" width="200"><br><sub><b>Bold</b></sub></td>
<td align="center"><img src="base/assets/home-styles/glitch.png" width="200"><br><sub><b>Glitch</b></sub></td>
<td align="center"><img src="base/assets/home-styles/pixel.png" width="200"><br><sub><b>Pixel</b></sub></td>
</tr>
<tr>
<td align="center"><img src="base/assets/home-styles/stencil.png" width="200"><br><sub><b>Stencil</b></sub></td>
<td align="center"><img src="base/assets/home-styles/racer.png" width="200"><br><sub><b>Racer</b></sub></td>
<td align="center"><img src="base/assets/home-styles/zen.png" width="200"><br><sub><b>Zen</b></sub></td>
<td align="center"><img src="base/assets/home-styles/cyber.png" width="200"><br><sub><b>Cyber</b></sub></td>
</tr>
<tr>
<td align="center"><img src="base/assets/home-styles/mono.png" width="200"><br><sub><b>Mono</b></sub></td>
<td align="center"><img src="base/assets/home-styles/sunset.png" width="200"><br><sub><b>Sunset</b></sub></td>
<td align="center"><img src="base/assets/home-styles/ocean.png" width="200"><br><sub><b>Ocean</b></sub></td>
<td align="center"><img src="base/assets/home-styles/aurora.png" width="200"><br><sub><b>Aurora</b></sub></td>
</tr>
<tr>
<td align="center"><img src="base/assets/home-styles/synthwave.png" width="200"><br><sub><b>Synthwave</b></sub></td>
<td align="center"><img src="base/assets/home-styles/forest.png" width="200"><br><sub><b>Forest</b></sub></td>
<td align="center"><img src="base/assets/home-styles/fire.png" width="200"><br><sub><b>Fire</b></sub></td>
<td align="center"><img src="base/assets/home-styles/ice.png" width="200"><br><sub><b>Ice</b></sub></td>
</tr>
<tr>
<td align="center"><img src="base/assets/home-styles/sunrise.png" width="200"><br><sub><b>Sunrise</b></sub></td>
<td align="center"><img src="base/assets/home-styles/tide.png" width="200"><br><sub><b>Tide</b></sub></td>
<td align="center"><img src="base/assets/home-styles/blueprint.png" width="200"><br><sub><b>Blueprint</b></sub></td>
<td align="center"><img src="base/assets/home-styles/paper.png" width="200"><br><sub><b>Paper</b></sub></td>
</tr>
</table>

<sub>Previews rendered at 320x240 with the device's own fonts; the panel itself
looks the same bar minor anti-aliasing.</sub>

Eight more: the **Station** family, same three sensors as the small row under
Dashboard's clock, drawn bigger and split differently - a big outdoor reading
up top, a small indoor temperature/humidity strip below a divider. Each
borrows its palette from the matching style above it - `Station Neon` is
`Neon`'s cyan and magenta, `Station Paper` is `Paper`'s cream and ink - except
`Station Aura`, which matches the `aura` character instead: its divider
freezes a single frame of the same line `aura.yaml` breathes on the character
screen.

<table>
<tr>
<td align="center"><img src="base/assets/home-styles/station.png" width="200"><br><sub><b>Station</b></sub></td>
<td align="center"><img src="base/assets/home-styles/station-aura.png" width="200"><br><sub><b>Station Aura</b></sub></td>
<td align="center"><img src="base/assets/home-styles/station-neon.png" width="200"><br><sub><b>Station Neon</b></sub></td>
<td align="center"><img src="base/assets/home-styles/station-amber.png" width="200"><br><sub><b>Station Amber</b></sub></td>
</tr>
<tr>
<td align="center"><img src="base/assets/home-styles/station-fire.png" width="200"><br><sub><b>Station Fire</b></sub></td>
<td align="center"><img src="base/assets/home-styles/station-ice.png" width="200"><br><sub><b>Station Ice</b></sub></td>
<td align="center"><img src="base/assets/home-styles/station-forest.png" width="200"><br><sub><b>Station Forest</b></sub></td>
<td align="center"><img src="base/assets/home-styles/station-paper.png" width="200"><br><sub><b>Station Paper</b></sub></td>
</tr>
</table>

`home.yaml` is parameterised, so the Default look is unchanged and any single
value - a colour, the clock font - can also be pinned at compile time by setting
its `home_*` substitution. Each style's clock font is a Google Font compiled in as
digits and a colon only, so the whole set adds a few KB. To add your own: a font,
a select option, and a branch in `apply_home_style`.

## Voice control

Two packages give Home Assistant's Assist (or any conversation agent) direct
control of the screen. Both are entities you press or call - nothing here is a
custom sentence or automation, on purpose.

### Switch screens by voice

Add `base/screens/show-screen.yaml` after `home.yaml`, `weather.yaml`,
`climate.yaml` and `media.yaml` (in any order, but after all four) and four
buttons appear in Home Assistant:

```yaml
  files:
    - base/core.yaml
    - base/screens/home.yaml
    - base/screens/weather.yaml
    - base/screens/climate.yaml
    - base/screens/media.yaml
    - base/screens/show-screen.yaml   # after all four
```

Expose **Show home screen**, **Show weather screen**, **Show thermostat
screen** and **Show media screen** to your Assist pipeline's conversation
agent and "Alexa, pokaż pogodę" jumps the display straight there.

**Four buttons, not one select.** An earlier version was a single "Show
screen" select with four options - simpler to expose, but Home Assistant's
OpenAI Conversation integration kept reaching for the generic `turn_on`
intent instead of `select.select_option`, which a select does not support,
and every call failed. A button only ever does one thing - press it - so
there is no service name or option value left for the model to get wrong.
This is the general lesson behind everything in this section: reduce the
action to the one shape a conversation agent reliably reaches for.

### Draw on screen

Add `base/screens/canvas.yaml` (needs nothing else) and Home Assistant can
draw rectangles, circles, text and Material Design icons on a blank
320x240 page, which the device switches to on its own. It is unreachable
any other way - no button, no swipe - on purpose: nothing on the Box names
it, so only Home Assistant can put it there.

```yaml
  files:
    - base/core.yaml
    - base/screens/canvas.yaml
```

The spec is a small pipe-delimited format, not JSON - elements separated by
`|`, fields within one element by `,`:

```
rect,X,Y,W,H,RADIUS,RRGGBB
circle,CX,CY,R,RRGGBB
text,X,Y,SIZE,RRGGBB,label text
icon,X,Y,SIZE,RRGGBB,name
```

SIZE for text is 0 (16px), 1 (24px) or 2 (40px); for icon, 0 (24px) or
anything else (48px). Colour is six hex digits, no `#`. Icon names: `sun
cloud partly-cloudy rain pouring snow snow-rain fog hail lightning storm
wind wind2 night alert thermometer humidity fire minus plus`. It does not
have to be data - "Alexa, draw something to cheer me up" is just circles
and a line of text, no diagonal lines needed here either:

```
circle,160,100,70,FFD700|circle,138,85,9,1B1F27|circle,182,85,9,1B1F27|circle,122,130,5,1B1F27|circle,135,142,5,1B1F27|circle,148,148,5,1B1F27|circle,160,150,5,1B1F27|circle,172,148,5,1B1F27|circle,185,142,5,1B1F27|circle,198,130,5,1B1F27|text,90,195,1,FFFFFF,A smile for you
```

<p align="center"><img src="base/assets/canvas-example.png" width="300" alt="Canvas screen showing a smiley face and the caption A smile for you"></p>

A bar chart works the same way, just rects of different heights,
bottom-aligned - see the [example Assist
instructions](#example-assist-instructions) below for that one.

**Nothing is auto-corrected - every coordinate has to land inside 320x240
yourself.** An element placed off-panel is simply invisible past the edge,
not shrunk, wrapped or moved back on screen; text in particular is a single
line that never wraps. This was a deliberate choice over having the engine
silently reposition anything: it keeps what a model computes and what
actually gets drawn identical, at the cost of the model needing the exact
bounds up front - which is what the script below gives it.

**Voice needs a script wrapper, and this one is required, not optional.**
Calling the entity or the service directly from Assist fails the same way
the screen-switching select did. Create this in Home Assistant (Settings ->
Automations & Scenes -> Scripts -> Add Script -> Edit in YAML), with your
own device's service name in place of the example one (check Developer
tools -> Actions, domain `esphome`, once `canvas.yaml` is flashed):

```yaml
alias: Draw on screen
description: >-
  Draws on the kitchen Box's screen. Canvas is exactly 320x240px, (0,0) top
  left. Nothing is auto-corrected - every element has to fit on its own.
fields:
  spec:
    name: Spec
    description: >-
      Canvas is EXACTLY 320x240px, (0,0) top-left. Nothing is auto-corrected -
      compute coordinates so every element fits inside 0..320 (X) and 0..240
      (Y) yourself. Elements separated by |, fields by comma.
      rect,X,Y,W,H,RADIUS,RRGGBB - keep X+W<=320 and Y+H<=240.
      circle,CX,CY,R,RRGGBB - keep CX-R>=0, CX+R<=320, CY-R>=0, CY+R<=240.
      text,X,Y,SIZE,RRGGBB,label - ONE line, never wraps; SIZE 0=16px tall
      (~8px/char), 1=24px (~12px/char), 2=40px (~20px/char) - keep
      Y+height<=240 and X+estimated width<=320, use SIZE 0 for long text.
      Always write numbers as digits ("20.3°C"), never spelled out in words.
      icon,X,Y,SIZE,RRGGBB,name - square, SIZE 0=24px or 1=48px - keep
      X+size<=320 and Y+size<=240. Icon names: sun cloud partly-cloudy rain
      pouring snow snow-rain fog hail lightning storm wind wind2 night alert
      thermometer humidity fire minus plus.
      Example: icon,140,70,1,FFD700,sun|text,60,140,1,FFFFFF,Sunny
    required: true
    selector:
      text:
sequence:
  - action: esphome.esp32_s3_box_3_va_draw_on_screen   # <- your device's service
    data:
      spec: "{{ spec }}"
mode: single
```

Expose this **script** (never the raw entity or service) to your Assist
pipeline's conversation agent.

There is also a plain `text` entity, "Draw on screen", for testing from the
Home Assistant UI without a script - it runs through the same drawing code,
but Home Assistant caps any entity's state at 255 characters, good for
roughly 8-12 short elements. The script above goes through the native API
service instead of an entity, so it has no such cap - the real ceiling
there is the widget pool, 30 elements (16 rect/circle + 8 text + 6 icon)
in one spec.

### Example Assist instructions

This is the full text, not a summary - paste it as-is into your
conversation agent's instructions (wherever your Assist pipeline's LLM
integration takes a system prompt) and both features are ready to use, no
filling in blanks:

```
You control a kitchen display. You can switch what it shows and draw on it.

SWITCHING SCREENS: press one of the four buttons - "Show home screen",
"Show weather screen", "Show thermostat screen", "Show media screen".
Each one only ever does the one thing its name says.

DRAWING: call the "Draw on screen" script with a `spec` field. The canvas
is EXACTLY 320x240 pixels, (0,0) is the top-left corner, and NOTHING is
auto-corrected - you must compute every coordinate yourself so each
element fits entirely inside 0..320 (X) and 0..240 (Y) before calling the
script. An element that runs past an edge is simply invisible past that
edge, not shrunk or moved back into view.

Format: elements separated by "|", fields within one element separated by
",". Four element types:

  rect,X,Y,W,H,RADIUS,RRGGBB
    A filled rectangle (RADIUS 0 = square corners). Keep X+W<=320 and
    Y+H<=240.

  circle,CX,CY,R,RRGGBB
    A filled circle, centre and radius. Keep CX-R>=0, CX+R<=320,
    CY-R>=0, CY+R<=240.

  text,X,Y,SIZE,RRGGBB,label text
    ONE line, it never wraps. SIZE 0 is 16px tall (roughly 8px per
    character), SIZE 1 is 24px tall (roughly 12px per character), SIZE 2
    is 40px tall (roughly 20px per character). Keep Y+height<=240 and
    X+(character count x px/char)<=320 - use SIZE 0 for anything longer
    than a few words. Always write numbers as digits ("20.3°C"), never
    spelled out in words.

  icon,X,Y,SIZE,RRGGBB,name
    One Material Design icon, drawn as a square. SIZE 0 is 24px, anything
    else is 48px. Keep X+size<=320 and Y+size<=240. `name` must be one of:
    sun, cloud, partly-cloudy, rain, pouring, snow, snow-rain, fog, hail,
    lightning, storm, wind, wind2, night, alert, thermometer, humidity,
    fire, minus, plus.

Colour is always six hex digits, no "#". A bar chart is just rects of
different heights, bottom-aligned - there are no diagonal lines.

Example - a small sun over "Sunny":
  icon,140,70,1,FFD700,sun|text,60,140,1,FFFFFF,Sunny

Example - three bars of a chart with labels underneath:
  rect,20,140,20,60,0,FF8A3D|rect,50,120,20,80,0,FF8A3D|rect,80,90,20,110,0,FF8A3D|text,20,205,0,8FA6C0,6|text,50,205,0,8FA6C0,12|text,80,205,0,8FA6C0,18
```

Both features work from a plain instruction because they already reduce
to the one action shape a conversation agent reliably calls - a button, or
a script with one field - so there is nothing left for the model to get
wrong about *which* service or option to use. Drawing still asks the model
to get coordinates right on its own (nothing here auto-corrects a mistake,
by design - see above), which is why this text spells out the exact pixel
budget instead of leaving it implied. The script's own field description
carries the identical bounds, so they still apply even if this
system-prompt text gets trimmed or forgotten later.

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
  the S3-Box-3 config this started as a port of.
- **[espressif/esp-bsp](https://github.com/espressif/esp-bsp)**: the authoritative
  BOX-3 pin map (`bsp/esp-box-3`).
- **ESPHome**: everything the firmware is built out of.
- **[Home Assistant Voice PE](https://github.com/esphome/home-assistant-voice-pe)**:
  the timer sound and the phase model.
