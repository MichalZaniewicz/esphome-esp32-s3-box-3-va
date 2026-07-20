# Characters

The assistant on screen is split in two: `base/screens/face.yaml` is the
**engine** - it draws two eyes and a mouth and animates them per phase - and a
file in here is a **character**: one image plus the numbers that say where its
features go. Swapping the assistant is one word: `assistant:`.

Whichever character is installed, it exposes the same page id, `page_face`, so a
config can point a phase at it without knowing which one is in use.

![The seven characters across five phases](../assets/characters.png)

Animated, one clip each: [aura](../assets/demo/demo-aura.gif) · [bit](../assets/demo/demo-bit.gif) · [pixel](../assets/demo/demo-pixel.gif) · [iris](../assets/demo/demo-iris.gif) · [rain](../assets/demo/demo-rain.gif) · [crt](../assets/demo/demo-crt.gif) · [jarvis](../assets/demo/demo-jarvis.gif) · [pip](../assets/demo/demo-pip.gif) · [astro](../assets/demo/demo-astro.gif) · [momo](../assets/demo/demo-momo.gif) · [franky](../assets/demo/demo-franky.gif) · [wizard](../assets/demo/demo-wizard.gif) · [genie](../assets/demo/demo-genie.gif) · [flare](../assets/demo/demo-flare.gif) · [kitt](../assets/demo/demo-kitt.gif) · [rhea](../assets/demo/demo-rhea.gif)

The preview image above shows only the characters that use artwork; `aura`, `bit`, `pixel`,
`iris`, `rain`, `crt`, `jarvis` and `kitt` draw themselves and are in the clips.

| Character | Look | Face style |
|---|---|---|
| **Pip** | Round head, antenna, blue panel | Soft cyan ovals. The reference - every other character was measured against it. |
| **Astro** | Astronaut, sealed visor | Cyan capsule slits. The visor is wide and shallow, profiled row by row; tall eyes do not fit. |
| **Momo** | Cat ears, black screen | Amber square pixels, barely rounded. The artwork has no colour of its own. |
| **Franky** | Green monster, bolts, stitches | White cartoon eyes with black pupils - the only face here that is skin rather than a display, so it gets a separate mouth colour. |
| **Wizard** | Void under a purple hat | Glowing gold eyes and almost no mouth. The void sits below the hat brim, not at the frame's centre. |
| **Genie** | Small head, big beard | The most compact face of the set; both features sit above the beard, which begins just below the mouth. |
| **Rhea** | Wavy brown hair, gold and blue | White cartoon eyes with brown pupils. The artwork arrived with closed-eye arcs already drawn near the fringe; they were kept as eyebrows and the real eyes placed in the clean area below, rather than repainting hair to erase them. |
| **Kitt** | No artwork at all | Two rails and nine segments, drawing itself. Nothing moves and nothing resizes: the sweep is brightness alone, nine colour writes per tick, which makes it the cheapest animation in the repo. |
| **Aura** | No artwork at all | Nine bars on a line: flat at rest, an equaliser while speaking. No eyes and no mouth, so it skips the engine entirely and draws itself. |
| **Bit** | No artwork at all | Two eyes with pupils and a small mouth on black. Draws itself. Started out as eyes only; the mouth was added because eyes alone cannot show speech, which left `replying` and `listening` looking identical. |
| **Iris** | No artwork at all | One eye filling the screen. Draws itself. Everything it does is a size change on the iris and pupil plus a height change on two eyelid rectangles, which is why it is the cheapest full-screen character here. |
| **Rain** | No artwork at all | Falling glyphs, drawing itself. Nothing moves: each column is a still label whose text is rewritten every tick. The brightness gradient down a trail needs LVGL's `recolor` markup, since one label otherwise carries one colour. |
| **CRT** | No artwork at all | A green terminal, drawing itself. Reads `text_request` and `text_response` from the core, so it prints what was said and types out the reply. The only character with words in it, and so the only one `base/lang/*.yaml` has to translate. |
| **Jarvis** | No artwork at all | A sci-fi HUD, drawing itself. Seven arc segments spun by writing `start_angle` and `end_angle` every tick, at two radii turning opposite ways. Its brackets and arc colours are deliberately fixed: both would need runtime properties this project has not proven, and a wrong guess there fails the build rather than looking odd. |
| **Pixel** | No artwork at all | A 12x8 LED matrix, drawing itself. Dots carry brightness rather than just on and off, and a pupil is an unlit dot inside a lit 3x3 eye, because at that density a separate pupil would not fit. |
| **Flare** | Burning blob, flames on top | Dark features cut into a bright body, with the pupil lit in the body's own yellow. The only inverted face here, and a useful demonstration that `face_color` need not be the bright one. |

`face_center_x` shifts the whole face sideways when the artwork is not centred.
Most of these do not need it - five of the six sit on the frame's axis and only
Wizard is off by 3 px. Measure before reaching for it: reading coordinates off a
scaled screenshot is exactly how a first pass got Franky and Genie wrong by 20 px
each. Compare the left and right halves of the image and find the axis where they
mirror; if that lands on 160, the offset is zero.

Every expression the engine draws, for reference:

![Expressions](../assets/face-expressions.png)

## Using one

```yaml
substitutions:
  assistant: pip

packages:
  core:
    url: https://github.com/MichalZaniewicz/esphome-esp32-s3-box-3-va
    files:
      - base/core.yaml
      - base/faces/${assistant}.yaml
    refresh: 0s
```

Naming the file is enough because a character declares its own `packages:` block
pulling `base/screens/face.yaml`. ESPHome collects a package's substitutions
before descending into its nested packages, and earlier-collected values win, so
the character's geometry beats the engine's defaults rather than the other way
round.

`aura`, `bit`, `pixel`, `iris`, `rain`, `crt`, `jarvis` and `kitt` are the exceptions: they have no
artwork and no engine, and draw themselves. Naming one is still all you do, which
is the point of a character pulling its own dependencies rather than the config
having to know which of them needs what.

Order still matters between siblings: the language package goes last, since
later-listed files win substitution conflicts.

## Adding one

1. **Draw the character with no face.** 320x240 PNG. The eyes and mouth are
   drawn on top at runtime, so leave the space where they belong empty. If you
   are adapting existing artwork that already has a face, erase it - the blank
   area needs to match whatever is behind it, or the drawn features will sit on
   a patch.
2. `cp pip.yaml mycharacter.yaml`, point `face_background_file` at your image,
   and adjust the geometry.
3. Measure rather than guess. Open your original artwork, note the pixel
   coordinates of the eyes and mouth, and convert them to offsets from the
   centre of a 320x240 frame (so centre is `160,120`; `face_eye_y: 36` means 36
   pixels *below* centre). That is how `pip.yaml` was built, and it landed
   right first time.
4. Pull requests welcome.

## What a character controls

| Group | Substitutions |
|---|---|
| Artwork | `face_background_file` |
| Colour | `face_color`, `face_alarm_color` |
| Resting shape | `face_eye_offset`, `face_eye_y`, `face_eye_w`, `face_eye_h`, `face_mouth_y`, `face_mouth_w`, `face_mouth_h` |
| Expressions | `face_eye_h_wide`, `face_eye_h_narrow`, `face_eye_h_shut`, `face_mouth_open_h`, `face_mouth_small_w`, `face_mouth_o_w`, `face_mouth_o_h`, `face_mouth_alarm_w`, `face_mouth_alarm_h`, `face_mouth_error_w` |
| Motion | `face_gaze_dx`, `face_shake_dx`, `face_idle_cycle`, `face_tick` |
| Corners | `face_eye_radius`, `face_mouth_radius` |

Every expression dimension is a substitution precisely so a character with a
larger or smaller face can rescale its whole range without editing the engine.
An eye is a rounded rectangle: give it a radius of half its height and it reads
as an oval, keep the radius small and it reads as a screen pixel block.

## Limits worth knowing before you design one

- **Two eyes and one mouth, all rectangles.** No eyebrows, no pupils, no curves.
  Expression comes from proportion and motion, which is enough - see the preview
  above - but a character that needs a frown will need the engine extended.
- **The background never redraws.** That is what keeps the animation cheap on
  this hardware, and it means the artwork cannot animate. Anything that should
  move has to be one of the three widgets.
- **Only the mouth speaks.** During a reply it opens and closes on a fixed
  cycle; it is not driven by the audio, which the box never sees when TTS is
  routed to an external player.
