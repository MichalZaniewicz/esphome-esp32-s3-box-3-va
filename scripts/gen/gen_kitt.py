"""Generuje base/faces/kitt.yaml - pasek skanera."""
import os

# Sciezka liczona wzgledem tego pliku, nie zaszyta na sztywno. Generatory zyly
# do 2026-07-20 w katalogu tymczasowym z absolutna sciezka do jednego dysku:
# nie dalo sie ich uruchomic nigdzie indziej, a skasowanie katalogu skasowaloby
# jedyne zrodlo tych plikow.
_FACES = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "base", "faces")
)
import io

N, PITCH, SEG_W, SEG_H = 9, 32, 26, 46
OUT = os.path.join(_FACES, "kitt.yaml")

HEAD = """###############################################################################
# Kitt - a scanner bar, in the manner of a certain talking car from the 1980s.
# Styled after the genre, not copied from it, and not affiliated with anyone.
#
# No artwork: two rails and __N__ segments whose brightness sweeps side to side.
# Like the other drawn characters it does NOT nest base/screens/face.yaml.
#
# NOTHING MOVES AND NOTHING CHANGES SIZE. The sweep is brightness alone: every
# tick computes a level 0..255 per segment and writes it as a colour. That makes
# this the cheapest animation in the repository - __N__ colour writes per tick and
# not one geometry change.
#
# The idle sweep is the whole point of this character, so unlike every other
# assistant here it is at its most recognisable when nothing is happening.
###############################################################################

substitutions:
  kitt_color: '0xFF2A18'
  kitt_dim_color: '0x2A0806'      # an unlit segment, not a black one: the bar
                                  # should still read as hardware when dark
  kitt_alarm_color: '0xFFB030'
  kitt_muted_color: '0x3A2A28'
  # Two thin rails above and below the segments instead of a box behind them.
  # A filled housing read as a grey slab with lights sitting on top; a pair of
  # rails reads as a slot the light is set into, and costs two objects.
  kitt_rail_color: '0x7A808C'
  kitt_rail_shadow: '0x3A3E46'
  kitt_rail_offset: '40'          # from centre, up and down
  kitt_bg_color: '0x08080A'
  kitt_seg_w: '__SEG_W__'
  kitt_seg_h: '__SEG_H__'
  kitt_seg_radius: '4'

  # Sweep speed, in hundredths of a segment per tick. Idle is deliberately
  # unhurried; thinking is the same motion driven hard.
  kitt_speed_idle: '28'
  kitt_speed_think: '90'
  # How far the glow bleeds into neighbouring segments, hundredths per segment.
  # Higher is a tighter point of light.
  kitt_spread_idle: '55'
  kitt_spread_think: '85'

  kitt_tick: 100ms

  # Claim every phase. `page_face` is the id every character exposes, so a
  # config can point a phase at the character without knowing which is installed.
  idle_page: page_face
  idle_page_alt: page_face
  listening_page: page_face
  thinking_page: page_face
  replying_page: page_face
  error_page: page_face
  muted_page: page_face
  timer_page: page_face

globals:
  - id: kitt_frame
    type: int
    restore_value: false
    initial_value: "0"
  - id: kitt_lv
    type: int[__N__]
    restore_value: false
  # Which colour the bar is wearing, so the draw lambdas do not each have to
  # work out the phase again.
  - id: kitt_lit
    type: int
    restore_value: false
    initial_value: "1"

esphome:
  on_boot:
    - priority: 800
      then:
        - logger.log:
            level: INFO
            format: "package: faces/kitt.yaml (scanner bar, no artwork)"

script:
  - id: kitt_compute
    then:
      - lambda: |-
          const int f = id(kitt_frame);
          const int phase = id(voice_assistant_phase);
          const float SPAN = __N__ - 1;

          int lit = 1;
          if (phase == ${voice_assist_timer_finished_phase_id} ||
              phase == ${voice_assist_error_phase_id}) lit = 2;
          if (phase == ${voice_assist_muted_phase_id}) lit = 3;
          id(kitt_lit) = lit;

          for (int i = 0; i < __N__; i++) {
            int v;

            if (phase == ${voice_assist_listening_phase_id}) {
              // Opens outwards from the middle: a bar reacting to a voice
              // rather than patrolling.
              const float w = fmodf(f * 0.30f, SPAN / 2.0f + 1.0f);
              const float d = fabsf(i - SPAN / 2.0f);
              v = (int) (255.0f * (1.0f - fabsf(d - w) * 0.75f));
              if (v < 30) v = 30;
            } else if (phase == ${voice_assist_thinking_phase_id}) {
              const float p = fmodf(f * ${kitt_speed_think} / 100.0f, SPAN * 2.0f);
              const float pos = (p < SPAN) ? p : (SPAN * 2.0f - p);
              v = (int) (255.0f * (1.0f - fabsf(i - pos) * ${kitt_spread_think} / 100.0f));
              if (v < 20) v = 20;
            } else if (phase == ${voice_assist_replying_phase_id}) {
              // Deterministic noise, the same trick the other drawn characters
              // use: busy without flickering.
              uint32_t n = (uint32_t) (f * 73 + i * 151);
              n = (n ^ (n >> 5)) * 2654435761u;
              v = 38 + (int) (((n >> 16) & 0xFF) * 217 / 255);
            } else if (lit == 2) {
              v = ((f / 2) % 2) ? 255 : 30;
            } else if (lit == 3) {
              v = 26;
            } else {
              // Idle: the slow patrol this character exists for.
              const float p = fmodf(f * ${kitt_speed_idle} / 100.0f, SPAN * 2.0f);
              const float pos = (p < SPAN) ? p : (SPAN * 2.0f - p);
              v = (int) (255.0f * (1.0f - fabsf(i - pos) * ${kitt_spread_idle} / 100.0f));
              if (v < 15) v = 15;
            }

            id(kitt_lv)[i] = v > 255 ? 255 : (v < 0 ? 0 : v);
          }

  - id: kitt_draw
    then:
__DRAW__

  - id: kitt_tick_script
    mode: single
    then:
      # WRAPPED, like every other character's counter. The idle patrol is what
      # this thing does almost all the time, and it drives fmodf(f * speed, ...)
      # - so an unbounded f is exactly the value that loses precision first, and
      # in the animation that is on screen most.
      - lambda: id(kitt_frame) = (id(kitt_frame) + 1) % 36000;
      - script.execute: kitt_compute
      - script.execute: kitt_draw

interval:
  - interval: ${kitt_tick}
    then:
      - if:
          condition:
            lvgl.page.is_showing: page_face
          then:
            - script.execute: kitt_tick_script

lvgl:
  pages:
    - id: page_face
      bg_color: ${kitt_bg_color}
      # No scrollbar. These pages are drawn to fill the screen and there is
      # nothing to scroll to, but content sized to exactly 240 px renders a hair
      # taller than the arithmetic says and LVGL then draws a bar down the right
      # hand side. Seen on `rain` on hardware 2026-07-22; every page here is the
      # same shape of risk, and turning it off costs nothing.
      scrollbar_mode: "OFF"
      widgets:
        - obj:
            id: kitt_rail_top
            align: CENTER
            x: 0
            y: -${kitt_rail_offset}
            width: 100%
            height: 4
            radius: 0
            bg_color: ${kitt_rail_color}
            bg_opa: COVER
            border_width: 0
            pad_all: 0
        - obj:
            id: kitt_rail_bottom
            align: CENTER
            x: 0
            y: ${kitt_rail_offset}
            width: 100%
            height: 4
            radius: 0
            bg_color: ${kitt_rail_shadow}
            bg_opa: COVER
            border_width: 0
            pad_all: 0
"""

# ONE lambda for all __N__ segments, not one lvgl.widget.update each.
#
# The per-segment form this replaced recomputed the same lit colour __N__ times a
# tick and pushed every result through ESPHome's style machinery, which never
# checks whether the value changed. In the idle sweep most segments hold their
# colour from one frame to the next, so nearly all of that was repainting
# identical pixels.
#
# THE YAML WAS EDITED DIRECTLY AND THIS GENERATOR WAS NOT, so running it would
# silently undo the optimisation - which is exactly what happened on 2026-07-20.
# scripts/validate.py now regenerates and diffs, so the two cannot drift apart
# again without the check failing.
DRAW_ALL = """      # One lambda instead of nine lvgl.widget.update actions, each of which
      # recomputed the same lit colour and pushed it through ESPHome's style
      # machinery. Only segments whose colour actually changed are written.
      - lambda: |-
          static lv_obj_t *seg[{n}] = {{{ids}}};
          static uint32_t seen[{n}];
          static bool primed = false;

          uint32_t lit = ${{kitt_color}};
          if (id(kitt_lit) == 2) lit = ${{kitt_alarm_color}};
          else if (id(kitt_lit) == 3) lit = ${{kitt_muted_color}};
          const uint32_t off = ${{kitt_dim_color}};

          for (int i = 0; i < {n}; i++) {{
            const int v = id(kitt_lv)[i];
            const int r = (int) ((off >> 16) & 0xFF) + ((int) ((lit >> 16) & 0xFF) - (int) ((off >> 16) & 0xFF)) * v / 255;
            const int g = (int) ((off >> 8) & 0xFF) + ((int) ((lit >> 8) & 0xFF) - (int) ((off >> 8) & 0xFF)) * v / 255;
            const int b = (int) (off & 0xFF) + ((int) (lit & 0xFF) - (int) (off & 0xFF)) * v / 255;
            const uint32_t packed = ((uint32_t) r << 16) | ((uint32_t) g << 8) | (uint32_t) b;
            if (primed && seen[i] == packed) continue;
            seen[i] = packed;
            lv_obj_set_style_bg_color(seg[i], lv_color_hex(packed), 0);
          }}
          primed = true;"""

SEG_ONE = """        - obj:
            id: kitt_seg_{i}
            align: CENTER
            x: {x}
            y: 0
            width: ${{kitt_seg_w}}
            height: ${{kitt_seg_h}}
            radius: ${{kitt_seg_radius}}
            bg_color: ${{kitt_dim_color}}
            bg_opa: COVER
            border_width: 0
            pad_all: 0"""

TAIL = """
        # Same contract as every other character screen: a tap silences a
        # ringing timer, or swaps idle screens when the config defines two.
        - button:
            id: kitt_tap
            width: 100%
            height: 100%
            bg_opa: TRANSP
            border_width: 0
            shadow_width: 0
            on_click:
              - if:
                  condition:
                    switch.is_on: timer_ringing
                  then:
                    - switch.turn_off: timer_ringing
                  else:
                    - if:
                        condition:
                          lambda: return id(voice_assistant_phase) == ${voice_assist_idle_phase_id};
                        then:
                          - script.execute: toggle_idle_screen
"""

draw = DRAW_ALL.format(n=N, ids=", ".join(f"id(kitt_seg_{i})" for i in range(N)))
segs = "\n".join(SEG_ONE.format(i=i, x=(i - (N - 1) // 2) * PITCH) for i in range(N))

body = (HEAD.replace("__N__", str(N))
            .replace("__SEG_W__", str(SEG_W))
            .replace("__SEG_H__", str(SEG_H))
            .replace("__DRAW__", draw)
        + segs + "\n" + TAIL)

io.open(OUT, "w", encoding="utf-8", newline="\n").write(body)
print(f"{OUT}: {len(body.splitlines())} linii, {N} segmentow")
