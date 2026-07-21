"""Generuje base/faces/scope.yaml i base/faces/vu.yaml.

Oba rysuja linie o punktach liczonych w locie. Akcja `lvgl.line.update` przyjmuje
punkty tylko jako stale z configu, wiec nie da sie ich policzyc na tick - lambda
wola wiec lv_line_set_points bezposrednio. UWAGA: id widgetu `line` to
LvLineType (dziedziczy po LvCompound), a nie lv_obj_t*, wiec wskaznik siedzi w
polu ->obj. LVGL nie kopiuje tablicy punktow, dlatego musi ona byc `static`.
"""
import os

# Sciezka liczona wzgledem tego pliku, nie zaszyta na sztywno. Generatory zyly
# do 2026-07-20 w katalogu tymczasowym z absolutna sciezka do jednego dysku:
# nie dalo sie ich uruchomic nigdzie indziej, a skasowanie katalogu skasowaloby
# jedyne zrodlo tych plikow.
_FACES = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "base", "faces")
)
import io
import math

R = _FACES + os.sep
NPT = 33                      # punktow sladu oscyloskopu
GX0, GY0, GX1, GY1 = 18, 34, 302, 206

# --------------------------------------------------------------------- SCOPE
SCOPE = """###############################################################################
# Scope - an oscilloscope trace on a measurement grid.
#
# No artwork. The grid is static objects; the only thing that moves is one line
# widget whose points are recomputed every tick.
#
# THIS IS THE ONLY CHARACTER THAT DRAWS A CONTINUOUS CURVE. Everything else in
# the set is built from rectangles, so shapes here are limited to bars and
# blocks. That is also why it needs a mechanism nothing else uses:
#
#   `lvgl.line.update` takes its points as CONFIG values, validated at build
#   time, so it cannot compute a waveform per tick. The lambda therefore calls
#   lv_line_set_points() itself. Two traps in doing that:
#
#   A LINE ID IS NOT AN lv_obj_t*. Plain `obj` widgets are, which is what pixel
#   and nixie rely on, but `line` is declared LvLineType and inherits LvCompound,
#   so the real pointer is `id(scope_trace)->obj`. Passing the id straight in
#   fails to compile - it cost one build to find out.
#
#   LVGL DOES NOT COPY THE POINTS. It keeps the pointer, so the array must be
#   `static` and outlive the call; a local one leaves the widget reading freed
#   stack.
#
# Each phase differs in SHAPE, not brightness, which is what keeps the phases
# apart: a flat line, a swelling wave, a rotating loop, a ragged voice print.
###############################################################################

substitutions:
  scope_trace_color: '0x5CFF8A'
  scope_grid_color: '0x10331C'
  scope_frame_color: '0x1E5A30'
  scope_alarm_color: '0xFF6A4A'
  scope_bg_color: '0x030C06'
  scope_label_color: '0x2E8A4A'

  scope_label: "CH1  20ms/div"
  scope_trace_width: '2'

  scope_tick: 100ms

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
  - id: scope_frame
    type: int
    restore_value: false
    initial_value: "0"
  # 0 = nothing painted yet, 1 = normal trace colour, 2 = alarm. Only used to
  # skip repainting a colour that is already on the widget.
  - id: scope_tint_state
    type: int
    restore_value: false
    initial_value: "0"

font:
  - id: font_scope
    file:
      type: gfonts
      family: Roboto Mono
      weight: 400
    size: 12
    glyphs: "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz /:.-"

esphome:
  on_boot:
    - priority: 800
      then:
        - logger.log:
            level: INFO
            format: "package: faces/scope.yaml (oscilloscope, no artwork)"

script:
  - id: scope_tick_script
    mode: single
    then:
      - lambda: |-
          // LVGL keeps the pointer, not the data, so this array has to outlive
          // the call. Static, not local.
          static lv_point_precise_t pts[__NPT__];

          // The envelope that fades the trace towards both edges depends only on
          // the point index, never on the frame or the phase, so it is a
          // constant table - but it was being rebuilt every tick: __NPT__ sinf
          // AND __NPT__ powf, ten times a second. powf has no hardware behind it
          // on this chip and is the most expensive call in the file.
          static float ENV[__NPT__];
          static bool env_ready = false;
          if (!env_ready) {
            for (int k = 0; k < __NPT__; k++)
              ENV[k] = powf(sinf(3.14159f * k / (__NPT__ - 1)), 0.6f);
            env_ready = true;
          }

          // WRAPPED. vu.yaml comes out of this same generator and has always
          // wrapped; scope did not, and it feeds f into every sinf it draws, so
          // it was the one that would eventually go coarse and jerky.
          const int f = id(scope_frame);
          id(scope_frame) = (f + 1) % 36000;
          const int phase = id(voice_assistant_phase);
          const float X0 = __GX0__, X1 = __GX1__;
          const float MID = (__GY0__ + __GY1__) / 2.0f;
          const float AMP = (__GY1__ - __GY0__) / 2.0f - 8.0f;
          const int N = __NPT__;

          auto rnd = [](int a, int b) {
            uint32_t n = (uint32_t) (a * 73 + b * 151);
            n = (n ^ (n >> 5)) * 2654435761u;
            return (int) ((n >> 16) & 0xFF);
          };

          if (phase == ${voice_assist_thinking_phase_id}) {
            // A Lissajous loop, turning. A closed figure reads as "working on
            // it" in a way no left-to-right trace does.
            for (int k = 0; k < N; k++) {
              const float t = (float) k / (N - 1) * 6.2831853f;
              pts[k].x = (lv_value_precise_t) (160.0f + (X1 - X0) / 2.6f * sinf(3.0f * t + f * 0.09f));
              pts[k].y = (lv_value_precise_t) (MID + AMP * 0.8f * sinf(2.0f * t));
            }
          } else {
            for (int k = 0; k < N; k++) {
              const float u = (float) k / (N - 1) * 6.2831853f;
              const float x = X0 + (X1 - X0) * k / (N - 1);
              float y;
              if (phase == ${voice_assist_listening_phase_id}) {
                // Deliberately not a textbook sine: the amplitude swells and
                // falls, a second harmonic spoils the perfect shape, and an
                // envelope fades the edges, so it reads as a signal coming in
                // rather than as a test pattern standing still.
                const float swell = 0.38f + 0.62f * (0.5f + 0.5f * sinf(f * 0.24f));
                const float env = ENV[k];
                const float wave = (sinf(u * 3.0f - f * 0.55f)
                                  + 0.38f * sinf(u * 7.0f - f * 0.95f)) / 1.38f;
                y = MID - AMP * 0.92f * swell * env * wave;
              } else if (phase == ${voice_assist_replying_phase_id}) {
                y = MID - AMP * ((rnd(f, k) / 255.0f) - 0.5f) * 1.7f;
              } else if (phase == ${voice_assist_timer_finished_phase_id} ||
                         phase == ${voice_assist_error_phase_id}) {
                y = MID - AMP * (((k / 4 + f) % 2) ? 0.9f : -0.9f);
              } else if (phase == ${voice_assist_muted_phase_id}) {
                y = MID;
              } else {
                y = MID - AMP * 0.06f * sinf(u * 3.0f - f * 0.12f);
              }
              pts[k].x = (lv_value_precise_t) x;
              pts[k].y = (lv_value_precise_t) y;
            }
          }
          // Only re-set the trace when a point actually moved, same reasoning as
          // the needles in vu below. This is the single most expensive write in
          // the character set: it dirties the trace widget's whole bounding box,
          // more than two passes of the draw buffer, and lv_line_set_points
          // never compares. In muted the shape is a flat constant, so the same
          // 33 points were being pushed ten times a second forever; the alarm
          // sawtooth repeats every other tick for the same reason.
          static lv_value_precise_t seen_x[__NPT__], seen_y[__NPT__];
          static bool primed = false;
          bool moved = !primed;
          if (primed) {
            for (int k = 0; k < N; k++) {
              if (pts[k].x != seen_x[k] || pts[k].y != seen_y[k]) { moved = true; break; }
            }
          }
          if (moved) {
            for (int k = 0; k < N; k++) { seen_x[k] = pts[k].x; seen_y[k] = pts[k].y; }
            primed = true;
            lv_line_set_points(id(scope_trace)->obj, pts, N);
          }

  # ONLY WHEN THE COLOUR ACTUALLY CHANGES. This used to run on every tick, ten
  # times a second, and it was the last place in the whole character set still
  # doing that. The colour has exactly two values and moves only when the phase
  # crosses into or out of alarm, so almost every call repainted what was
  # already there - and lvgl.widget.update never compares. It is not a cheap
  # repaint either: the trace widget spans __GW__x__GH__ px, more than two
  # passes of the draw buffer, on top of what lv_line_set_points already dirties.
  - id: scope_tint
    then:
      - if:
          condition:
            lambda: |-
              const int p = id(voice_assistant_phase);
              const int want = (p == ${voice_assist_timer_finished_phase_id} ||
                                p == ${voice_assist_error_phase_id}) ? 2 : 1;
              if (want == id(scope_tint_state)) return false;
              id(scope_tint_state) = want;
              return true;
          then:
            - lvgl.widget.update:
                id: scope_trace
                line_color: !lambda |-
                  const int p = id(voice_assistant_phase);
                  if (p == ${voice_assist_timer_finished_phase_id} ||
                      p == ${voice_assist_error_phase_id}) return lv_color_hex(${scope_alarm_color});
                  return lv_color_hex(${scope_trace_color});

interval:
  - interval: ${scope_tick}
    then:
      - if:
          condition:
            lvgl.page.is_showing: page_face
          then:
            - script.execute: scope_tick_script
            - script.execute: scope_tint

lvgl:
  pages:
    - id: page_face
      bg_color: ${scope_bg_color}
      widgets:
__GRID__
        - label:
            id: scope_label
            align: TOP_LEFT
            x: 20
            y: 12
            text: "${scope_label}"
            text_font: font_scope
            text_color: ${scope_label_color}
            pad_all: 0
        # The trace goes last so it draws over the grid. Its points are set from
        # the lambda above; the two here are only a placeholder for the schema.
        - line:
            id: scope_trace
            align: TOP_LEFT
            x: 0
            y: 0
            points:
              - __GX0__, __MIDY__
              - __GX1__, __MIDY__
            line_width: ${scope_trace_width}
            line_color: ${scope_trace_color}

        # Same contract as every other character screen: a tap silences a
        # ringing timer, or swaps idle screens when the config defines two.
        - button:
            id: scope_tap
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

grid = []
for k in range(7):
    x = int(GX0 + (GX1 - GX0) * k / 6)
    grid.append(f"""        - obj:
            id: scope_v{k}
            align: TOP_LEFT
            x: {x}
            y: {GY0}
            width: 1
            height: {GY1 - GY0}
            radius: 0
            bg_color: ${{scope_grid_color}}
            bg_opa: COVER
            border_width: 0
            pad_all: 0""")
for k in range(5):
    y = int(GY0 + (GY1 - GY0) * k / 4)
    grid.append(f"""        - obj:
            id: scope_h{k}
            align: TOP_LEFT
            x: {GX0}
            y: {y}
            width: {GX1 - GX0}
            height: 1
            radius: 0
            bg_color: ${{scope_grid_color}}
            bg_opa: COVER
            border_width: 0
            pad_all: 0""")
grid.append(f"""        - obj:
            id: scope_frame_box
            align: TOP_LEFT
            x: {GX0}
            y: {GY0}
            width: {GX1 - GX0}
            height: {GY1 - GY0}
            radius: 0
            bg_opa: TRANSP
            border_width: 2
            border_color: ${{scope_frame_color}}
            pad_all: 0""")

scope = (SCOPE.replace("__GRID__", "\n".join(grid))
              .replace("__NPT__", str(NPT))
              .replace("__GX0__", str(GX0)).replace("__GX1__", str(GX1))
              .replace("__GY0__", str(GY0)).replace("__GY1__", str(GY1))
              .replace("__GW__", str(GX1 - GX0)).replace("__GH__", str(GY1 - GY0))
              .replace("__MIDY__", str((GY0 + GY1) // 2)))
io.open(R + "scope.yaml", "w", encoding="utf-8", newline="\n").write(scope)
print(f"scope.yaml: {len(scope.splitlines())} linii")


# ------------------------------------------------------------------------ VU
VU_HEAD = """###############################################################################
# VU - two analogue meters with swinging needles.
#
# No artwork: two housings, two faces, the scale marks, a red zone and two
# needles. Like the other drawn characters it does NOT nest
# base/screens/face.yaml.
#
# A needle has to pivot, and LVGL cannot rotate a rectangle. So a needle is a
# LINE of two points, and the lambda writes those points itself with
# lv_line_set_points() - `lvgl.line.update` only takes points fixed at build
# time. Two things that are easy to get wrong: a line id is an LvLineType, not
# an lv_obj_t*, so the pointer is `id(vu_needle_l)->obj`; and LVGL keeps the
# points array rather than copying it, so it has to be `static`.
#
# Everything else is nailed down: the faces, the scale marks and the red zone are
# built once and never touched, so a tick costs exactly two needle writes.
###############################################################################

substitutions:
  vu_face_color: '0xE8DCC0'       # warm paper, not white
  vu_ink_color: '0x2A2218'
  vu_red_color: '0xC43628'
  vu_needle_color: '0x1A1410'
  vu_case_color: '0x221C14'
  vu_bg_color: '0x14100A'

  vu_swing: '50'                  # degrees either side of centre

  vu_tick: 100ms

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
  - id: vu_frame
    type: int
    restore_value: false
    initial_value: "0"

font:
  - id: font_vu
    file:
      type: gfonts
      family: Roboto Mono
      weight: 500
    size: 12
    glyphs: "VU"

esphome:
  on_boot:
    - priority: 800
      then:
        - logger.log:
            level: INFO
            format: "package: faces/vu.yaml (analogue meters, no artwork)"

script:
  - id: vu_tick_script
    mode: single
    then:
      - lambda: |-
          // One static pair of points per needle: LVGL keeps the pointer.
          static lv_point_precise_t left[2], right[2];
          lv_point_precise_t *pts[2] = {left, right};
          static const int PIVOT_X[2] = {__PX0__, __PX1__};
          const int PIVOT_Y = __PY__, LEN = __LEN__;

          // Wrapped: a free-running counter eventually costs sinf() its precision.
          const int f = id(vu_frame);
          id(vu_frame) = (f + 1) % 36000;
          const int phase = id(voice_assistant_phase);

          auto rnd = [](int a, int b) {
            uint32_t n = (uint32_t) (a * 73 + b * 151);
            n = (n ^ (n >> 5)) * 2654435761u;
            return (int) ((n >> 16) & 0xFF);
          };

          for (int s = 0; s < 2; s++) {
            float deg;
            if (phase == ${voice_assist_listening_phase_id}) {
              deg = -${vu_swing} + 78.0f * (0.5f + 0.5f * sinf(f * 0.28f - s * 0.3f));
            } else if (phase == ${voice_assist_thinking_phase_id}) {
              deg = -44.0f + 12.0f * sinf(f * 0.8f + s);
            } else if (phase == ${voice_assist_replying_phase_id}) {
              deg = -${vu_swing} + 100.0f * (rnd(f, s * 5) / 255.0f);
            } else if (phase == ${voice_assist_timer_finished_phase_id} ||
                       phase == ${voice_assist_error_phase_id}) {
              deg = ((f + s) % 2) ? 45.0f : -45.0f;
            } else if (phase == ${voice_assist_muted_phase_id}) {
              deg = -${vu_swing};
            } else {
              // Idle: resting near zero, with just enough tremble to look live.
              deg = -48.0f + 3.0f * sinf(f * 0.18f + s * 2.0f);
            }
            const float a = deg * 3.14159265f / 180.0f;
            pts[s][0].x = (lv_value_precise_t) PIVOT_X[s];
            pts[s][0].y = (lv_value_precise_t) PIVOT_Y;
            pts[s][1].x = (lv_value_precise_t) (PIVOT_X[s] + LEN * sinf(a));
            pts[s][1].y = (lv_value_precise_t) (PIVOT_Y - LEN * cosf(a));
          }
          // Only re-set a needle whose tip actually moved. In muted the angle
          // is a constant, so both needles were being re-set and re-invalidated
          // ten times a second at a fixed position, and idle's small tremble
          // repeats the same integer tip across several ticks.
          static lv_value_precise_t seen_x[2] = {-1, -1}, seen_y[2] = {-1, -1};
          for (int s = 0; s < 2; s++) {
            if (pts[s][1].x == seen_x[s] && pts[s][1].y == seen_y[s]) continue;
            seen_x[s] = pts[s][1].x;
            seen_y[s] = pts[s][1].y;
            lv_line_set_points(s == 0 ? id(vu_needle_l)->obj : id(vu_needle_r)->obj,
                               s == 0 ? left : right, 2);
          }

interval:
  - interval: ${vu_tick}
    then:
      - if:
          condition:
            lvgl.page.is_showing: page_face
          then:
            - script.execute: vu_tick_script

lvgl:
  pages:
    - id: page_face
      bg_color: ${vu_bg_color}
      widgets:
"""

VU_TAIL = """
        # Same contract as every other character screen: a tap silences a
        # ringing timer, or swaps idle screens when the config defines two.
        - button:
            id: vu_tap
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

PX = (82, 238)
PY, RAD, LEN = 150, 74, 60
vw = []
for s, cx in enumerate(PX):
    side = "l" if s == 0 else "r"
    vw.append(f"""        - obj:
            id: vu_case_{side}
            align: TOP_LEFT
            x: {cx - 72}
            y: 42
            width: 144
            height: 154
            radius: 8
            bg_color: ${{vu_case_color}}
            bg_opa: COVER
            border_width: 0
            pad_all: 0
        - obj:
            id: vu_face_{side}
            align: TOP_LEFT
            x: {cx - 64}
            y: 50
            width: 128
            height: 122
            radius: 6
            bg_color: ${{vu_face_color}}
            bg_opa: COVER
            border_width: 0
            pad_all: 0""")
    # Podzialka: kreski pod katem, wiec kazda to osobna, nieruchoma linia.
    for k in range(11):
        a = math.radians(-50 + k * 10)
        r1 = RAD - 8
        r2 = RAD - (18 if k % 5 == 0 else 13)
        x1, y1 = cx + r1 * math.sin(a), PY - r1 * math.cos(a)
        x2, y2 = cx + r2 * math.sin(a), PY - r2 * math.cos(a)
        col = "${vu_red_color}" if k >= 8 else "${vu_ink_color}"
        vw.append(f"""        - line:
            id: vu_t{side}{k}
            align: TOP_LEFT
            x: 0
            y: 0
            points:
              - {int(round(x1))}, {int(round(y1))}
              - {int(round(x2))}, {int(round(y2))}
            line_width: 2
            line_color: {col}""")
    vw.append(f"""        - label:
            id: vu_cap_{side}
            align: TOP_LEFT
            x: {cx - 11}
            y: 118
            text: "VU"
            text_font: font_vu
            text_color: ${{vu_ink_color}}
            pad_all: 0
        - arc:
            id: vu_red_{side}
            align: TOP_LEFT
            x: {cx - RAD + 10}
            y: {PY - RAD + 10}
            width: {2 * (RAD - 10)}
            height: {2 * (RAD - 10)}
            start_angle: 300
            end_angle: 322
            min_value: 0
            max_value: 100
            value: 100
            adjustable: false
            arc_opa: TRANSP
            arc_width: 4
            indicator:
              arc_color: ${{vu_red_color}}
              arc_width: 4
            knob:
              bg_opa: TRANSP
            pad_all: 0""")

for s, cx in enumerate(PX):
    side = "l" if s == 0 else "r"
    vw.append(f"""        - line:
            id: vu_needle_{side}
            align: TOP_LEFT
            x: 0
            y: 0
            points:
              - {cx}, {PY}
              - {cx}, {PY - LEN}
            line_width: 3
            line_color: ${{vu_needle_color}}
        - obj:
            id: vu_pivot_{side}
            align: TOP_LEFT
            x: {cx - 6}
            y: {PY - 6}
            width: 12
            height: 12
            radius: 6
            bg_color: ${{vu_needle_color}}
            bg_opa: COVER
            border_width: 0
            pad_all: 0""")

vu = (VU_HEAD.replace("__PX0__", str(PX[0])).replace("__PX1__", str(PX[1]))
             .replace("__PY__", str(PY)).replace("__LEN__", str(LEN))
      + "\n".join(vw) + "\n" + VU_TAIL)
io.open(R + "vu.yaml", "w", encoding="utf-8", newline="\n").write(vu)
print(f"vu.yaml: {len(vu.splitlines())} linii")
