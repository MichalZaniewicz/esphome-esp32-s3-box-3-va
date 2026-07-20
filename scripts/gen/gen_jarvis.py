"""Generuje base/faces/jarvis.yaml - interfejs w stylu science fiction."""
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

OUT = os.path.join(_FACES, "jarvis.yaml")
N_OUT, N_IN = 3, 4          # segmenty pierscienia zewnetrznego i wewnetrznego
N_TICK = 12
R_TICK_1, R_TICK_2, R_TICK_LONG = 51, 55, 60

HEAD = """###############################################################################
# Jarvis - a heads-up display, in the manner of a certain film franchise's
# fictional assistant. Styled after the genre, not copied from it, and not
# affiliated with or endorsed by anyone.
#
# No artwork: two rings, seven rotating arc segments, a pulsing core, corner
# brackets and a ring of tick marks. Like the other drawn characters it does NOT
# nest base/screens/face.yaml.
#
# The rotation is the whole trick: seven arcs at two radii, turning at different
# speeds in opposite directions, which is what makes it look mechanical rather
# than merely animated.
#
# WHY THE HUD IS THIS SIZE, AND NOT BIGGER. The core's draw buffer is 25% of
# the screen, 19200 px. LVGL renders a dirty area in bands that fit that buffer,
# redrawing every widget intersecting each band. The first version put the arcs
# on a 200 px circle: 40000 px of dirty area, three bands, three passes over
# seven of the most expensive shapes LVGL draws - the device measured 250-326 ms
# per LVGL operation and could not keep up with a 150 ms tick.
#
# Everything that moves now fits inside 85x85 = 7225 px, one band, one pass,
# with plenty of room under the 19200. Arc thickness was deliberately NOT scaled
# down with the rest: below about 3 px an arc stops reading as a line at all.
# The rings and the tick marks sit deliberately OUTSIDE that box, so they are
# never caught in the redraw at all. If you enlarge the arcs, check this sum
# again: crossing 19200 costs a whole extra pass over the whole area.
#
# HOW THE ARCS ARE TURNED, AND WHY NOT THE OBVIOUS WAY. `lvgl.arc.update` can
# set start_angle and end_angle, and that is how this was written first - but it
# routes each property through ESPHome's style machinery, so fourteen style
# recalculations and invalidations per tick, on the largest shapes on the screen.
# On the device it crawled. The lambda now calls lv_arc_set_bg_angles() once per
# arc instead, and skips any arc whose whole-degree angle has not moved since the
# last tick, which at idle speed is most of them.
#
# An arc id is an `lv_arc_t *`. That is neither a bare lv_obj_t* (what plain
# `obj` widgets are) nor an LvCompound (what `line` widgets are, reached through
# ->obj). Its first member is an lv_obj_t, so the cast below is the one LVGL
# itself relies on.
#
# WHAT DELIBERATELY DOES NOT MOVE, and why:
#
#   The corner brackets are fixed. Pulling them inward while listening looked
#   good in the sketch, but it needs the `y` coordinate written at runtime, and
#   the only coordinate this project has actually proven on hardware is `x`. A
#   wrong guess there is a build failure, not a cosmetic flaw, so the effect was
#   dropped rather than gambled on.
#
#   The arcs keep their colour in every phase. Recolouring them means writing to
#   a widget's INDICATOR part at runtime, which is again unproven here. The
#   alarm reads through the core going red and the rings spinning hard instead,
#   both of which use properties the face engine already relies on.
###############################################################################

substitutions:
  jarvis_color: '0xF5C542'          # the rings
  jarvis_hot_color: '0xFFE9A8'      # inner segments and the core's centre
  jarvis_dim_color: '0x6A5218'      # structure: rings, minor ticks
  jarvis_alarm_color: '0xFF5A3C'
  jarvis_muted_color: '0x4A4A3A'
  jarvis_bg_color: '0x04060A'

  jarvis_arc_w: '4'                 # outer segment thickness
  jarvis_arc_in_w: '3'

  # Core radii per phase. The core is the only part that changes size, so it
  # carries most of the character: small and still when idle, wide open while
  # listening, tight while thinking, pulsing while speaking.
  jarvis_core_idle: '9'
  jarvis_core_listen: '14'
  jarvis_core_think: '8'
  jarvis_core_reply: '11'
  jarvis_core_alarm: '17'
  jarvis_core_ring: '3'             # width of the core's outer band

  # Degrees per tick, outer ring then inner. Negative inner means the two rings
  # counter-rotate, which is what stops it reading as one spinning wheel.
  jarvis_spin_idle: '1.2'
  jarvis_spin_idle_in: '-0.75'
  jarvis_spin_listen: '2.4'
  jarvis_spin_listen_in: '-1.65'
  jarvis_spin_think: '10.5'
  jarvis_spin_think_in: '-7.5'
  jarvis_spin_reply: '3.3'
  jarvis_spin_reply_in: '-2.4'
  jarvis_spin_alarm: '6.0'
  jarvis_spin_alarm_in: '-6.0'

  # How long each segment is, in degrees. Short segments read as fast and busy.
  jarvis_span_idle: '38'
  jarvis_span_listen: '46'
  jarvis_span_think: '22'
  jarvis_span_reply: '40'
  jarvis_span_alarm: '30'

  # 150 ms, not 100: seven arcs redrawing a 200 px circle is the heaviest
  # thing on this screen, and at 100 ms the device could not keep up. The
  # spin figures below are scaled to match, so it turns at the same speed.
  jarvis_tick: 150ms

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
  - id: jarvis_frame
    type: int
    restore_value: false
    initial_value: "0"
  - id: jarvis_expr
    type: int
    restore_value: false
    initial_value: "0"
  # Angles are accumulated rather than derived from the frame count, so a change
  # of speed carries on from where the ring already is instead of jumping.
  - id: jarvis_rot_out
    type: float
    restore_value: false
    initial_value: "0.0"
  - id: jarvis_rot_in
    type: float
    restore_value: false
    initial_value: "0.0"
  - id: jarvis_span
    type: int
    restore_value: false
    initial_value: "${jarvis_span_idle}"
  - id: jarvis_core
    type: int
    restore_value: false
    initial_value: "${jarvis_core_idle}"

esphome:
  on_boot:
    - priority: 800
      then:
        - logger.log:
            level: INFO
            format: "package: faces/jarvis.yaml (sci-fi HUD, no artwork)"

script:
  - id: jarvis_compute
    then:
      - lambda: |-
          const int phase = id(voice_assistant_phase);
          // Wrapped: a free-running counter degrades sinf() precision over days.
          const int f = id(jarvis_frame) % 36000;

          float so = ${jarvis_spin_idle}, si = ${jarvis_spin_idle_in};
          int span = ${jarvis_span_idle};
          int core = ${jarvis_core_idle};

          if (phase == ${voice_assist_listening_phase_id}) {
            so = ${jarvis_spin_listen}; si = ${jarvis_spin_listen_in};
            span = ${jarvis_span_listen};
            core = ${jarvis_core_listen} + (int) (4.0f * sinf(f * 0.35f));
          } else if (phase == ${voice_assist_thinking_phase_id}) {
            so = ${jarvis_spin_think}; si = ${jarvis_spin_think_in};
            span = ${jarvis_span_think};
            core = ${jarvis_core_think};
          } else if (phase == ${voice_assist_replying_phase_id}) {
            so = ${jarvis_spin_reply}; si = ${jarvis_spin_reply_in};
            span = ${jarvis_span_reply};
            // Deterministic noise, same trick as the other drawn characters.
            uint32_t n = (uint32_t) (f * 73 + 151);
            n = (n ^ (n >> 5)) * 2654435761u;
            core = ${jarvis_core_reply} + (int) (((n >> 16) & 0xFF) * 16 / 255);
          } else if (phase == ${voice_assist_timer_finished_phase_id} ||
                     phase == ${voice_assist_error_phase_id}) {
            so = ${jarvis_spin_alarm}; si = ${jarvis_spin_alarm_in};
            span = ${jarvis_span_alarm};
            core = ${jarvis_core_alarm};
          } else if (phase == ${voice_assist_muted_phase_id}) {
            so = 0.0f; si = 0.0f;
            core = ${jarvis_core_think};
          } else {
            core = ${jarvis_core_idle} + (int) (2.0f * sinf(f * 0.09f));
          }

          id(jarvis_rot_out) = fmodf(id(jarvis_rot_out) + so + 360.0f, 360.0f);
          id(jarvis_rot_in) = fmodf(id(jarvis_rot_in) + si + 360.0f, 360.0f);
          id(jarvis_span) = span;
          id(jarvis_core) = core;

  - id: jarvis_draw
    then:
__DRAW__
      # The core, the same way as the arcs. It was still going through
      # lvgl.widget.update - the exact thing this file's header argues against -
      # and in thinking and muted its size is a constant, so those were four
      # property writes per tick that could never change anything.
      - lambda: |-
          static int seen_core = -1;
          const int c = id(jarvis_core);
          if (seen_core == c) return;
          seen_core = c;
          lv_obj_set_width((lv_obj_t *) id(jarvis_core_outer), c * 2);
          lv_obj_set_height((lv_obj_t *) id(jarvis_core_outer), c * 2);
          const int inner = (c - ${jarvis_core_ring}) * 2;
          lv_obj_set_width((lv_obj_t *) id(jarvis_core_inner), inner);
          lv_obj_set_height((lv_obj_t *) id(jarvis_core_inner), inner);

  - id: jarvis_tint_normal
    then:
      - lvgl.widget.update:
          id: jarvis_core_outer
          bg_color: ${jarvis_color}
      - lvgl.widget.update:
          id: jarvis_core_inner
          bg_color: ${jarvis_hot_color}

  - id: jarvis_tint_alarm
    then:
      - lvgl.widget.update:
          id: jarvis_core_outer
          bg_color: ${jarvis_alarm_color}
      - lvgl.widget.update:
          id: jarvis_core_inner
          bg_color: ${jarvis_alarm_color}

  - id: jarvis_tint_dim
    then:
      - lvgl.widget.update:
          id: jarvis_core_outer
          bg_color: ${jarvis_muted_color}
      - lvgl.widget.update:
          id: jarvis_core_inner
          bg_color: ${jarvis_muted_color}

  - id: jarvis_tick_script
    mode: single
    then:
      - lambda: id(jarvis_frame)++;
      - if:
          condition:
            lambda: |-
              const int p = id(voice_assistant_phase);
              int want = 1;
              if (p == ${voice_assist_timer_finished_phase_id} || p == ${voice_assist_error_phase_id}) want = 2;
              if (p == ${voice_assist_muted_phase_id}) want = 3;
              if (want == id(jarvis_expr)) return false;
              id(jarvis_expr) = want;
              return true;
          then:
            - if:
                condition:
                  lambda: return id(jarvis_expr) == 2;
                then:
                  - script.execute: jarvis_tint_alarm
            - if:
                condition:
                  lambda: return id(jarvis_expr) == 3;
                then:
                  - script.execute: jarvis_tint_dim
            - if:
                condition:
                  lambda: return id(jarvis_expr) == 1;
                then:
                  - script.execute: jarvis_tint_normal
      - script.execute: jarvis_compute
      - script.execute: jarvis_draw

interval:
  - interval: ${jarvis_tick}
    then:
      - if:
          condition:
            lvgl.page.is_showing: page_face
          then:
            - script.execute: jarvis_tick_script

lvgl:
  pages:
    - id: page_face
      bg_color: ${jarvis_bg_color}
      widgets:
        # Structure first: rings are objects with no fill and a border, which is
        # the cheapest circle outline LVGL offers.
        - obj:
            id: jarvis_ring_outer
            align: CENTER
            x: 0
            y: 0
            width: 95
            height: 95
            radius: 120
            bg_opa: TRANSP
            border_width: 1
            border_color: ${jarvis_dim_color}
            pad_all: 0
        - obj:
            id: jarvis_ring_inner
            align: CENTER
            x: 0
            y: 0
            width: 66
            height: 66
            radius: 120
            bg_opa: TRANSP
            border_width: 2
            border_color: ${jarvis_dim_color}
            pad_all: 0
"""

# --- luki -------------------------------------------------------------------
arcs, draw = [], []


def arc_block(wid, size, width, colour, start, span):
    return f"""        - arc:
            id: {wid}
            align: CENTER
            x: 0
            y: 0
            width: {size}
            height: {size}
            start_angle: {start}
            end_angle: {start + span}
            min_value: 0
            max_value: 100
            value: 100
            adjustable: false
            # The background arc is invisible; only the indicator is drawn, and
            # value 100 fills it right across start_angle..end_angle.
            arc_opa: TRANSP
            arc_width: {width}
            indicator:
              arc_color: {colour}
              arc_width: {width}
            knob:
              bg_opa: TRANSP
            pad_all: 0"""


for k in range(N_OUT):
    base = k * (360 // N_OUT)
    arcs.append(arc_block(f"jarvis_arc_out_{k}", 85, "${jarvis_arc_w}",
                          "${jarvis_color}", base, 38))
for k in range(N_IN):
    base = k * (360 // N_IN)
    arcs.append(arc_block(f"jarvis_arc_in_{k}", 56, "${jarvis_arc_in_w}",
                          "${jarvis_hot_color}", base, 22))

# Wszystkie luki jedna lambda. `lvgl.arc.update` ustawia kat przez maszynerie
# stylow ESPHome, czyli przeliczenie stylu i uniewaznienie na KAZDA z czternastu
# wlasciwosci co tick - to bylo zrodlo zamulenia. lv_arc_set_bg_angles robi to
# jednym wywolaniem na luk. Id luku jest typu lv_arc_t*, ktorego pierwszym polem
# jest lv_obj_t, wiec rzutowanie jest tym samym, co robi samo LVGL.
ptr_out = ", ".join(f"(lv_obj_t *) id(jarvis_arc_out_{k})" for k in range(N_OUT))
ptr_in = ", ".join(f"(lv_obj_t *) id(jarvis_arc_in_{k})" for k in range(N_IN))
draw.append(f"""      - lambda: |-
          static lv_obj_t *out[{N_OUT}] = {{{ptr_out}}};
          static lv_obj_t *inn[{N_IN}] = {{{ptr_in}}};
          static int seen_o[{N_OUT}], seen_i[{N_IN}];
          static bool primed = false;

          const int span = id(jarvis_span);
          // The span is phase-dependent but was NOT part of the skip key, and
          // muted freezes the rotation (spin 0), so the angle stops changing
          // too. Entering muted from thinking left all seven arcs stuck at the
          // 22 degree thinking span for the whole phase.
          static int seen_span = -1;
          const bool respan = (seen_span != span);
          seen_span = span;
          for (int k = 0; k < {N_OUT}; k++) {{
            const int a = ((int) id(jarvis_rot_out) + k * {360 // N_OUT}) % 360;
            // Kat jest calkowity, wiec przy powolnym obrocie wiekszosc tickow
            // nie zmienia nic - wtedy nie ruszamy widgetu w ogole.
            if (primed && !respan && seen_o[k] == a) continue;
            seen_o[k] = a;
            lv_arc_set_bg_angles(out[k], a, (a + span) % 360);
          }}
          for (int k = 0; k < {N_IN}; k++) {{
            const int a = ((int) id(jarvis_rot_in) + k * {360 // N_IN}) % 360;
            if (primed && !respan && seen_i[k] == a) continue;
            seen_i[k] = a;
            lv_arc_set_bg_angles(inn[k], a, (a + span * 3 / 5) % 360);
          }}
          primed = true;""")

# --- podzialka --------------------------------------------------------------
ticks = []
for k in range(N_TICK):
    a = math.radians(k * (360 / N_TICK))
    r2 = R_TICK_LONG if k % 3 == 0 else R_TICK_2
    x1, y1 = 160 + R_TICK_1 * math.cos(a), 120 + R_TICK_1 * math.sin(a)
    x2, y2 = 160 + r2 * math.cos(a), 120 + r2 * math.sin(a)
    col = "${jarvis_color}" if k % 3 == 0 else "${jarvis_dim_color}"
    ticks.append(f"""        - line:
            id: jarvis_tick_{k}
            align: TOP_LEFT
            x: 0
            y: 0
            points:
              - {int(round(x1))}, {int(round(y1))}
              - {int(round(x2))}, {int(round(y2))}
            line_width: 2
            line_color: {col}""")

# --- wsporniki w rogach -----------------------------------------------------
brackets = []
ARM, TH, INSET = 34, 3, 16
for sx, sy, nx, ny in ((-1, -1, "LEFT", "TOP"), (1, -1, "RIGHT", "TOP"),
                       (-1, 1, "LEFT", "BOTTOM"), (1, 1, "RIGHT", "BOTTOM")):
    align = f"{ny}_{nx}"
    brackets.append(f"""        - obj:
            id: jarvis_br_{ny.lower()}_{nx.lower()}_h
            align: {align}
            x: {sx * -INSET}
            y: {sy * -INSET}
            width: {ARM}
            height: {TH}
            radius: 0
            bg_color: ${{jarvis_color}}
            bg_opa: COVER
            border_width: 0
            pad_all: 0
        - obj:
            id: jarvis_br_{ny.lower()}_{nx.lower()}_v
            align: {align}
            x: {sx * -INSET}
            y: {sy * -INSET}
            width: {TH}
            height: {ARM}
            radius: 0
            bg_color: ${{jarvis_color}}
            bg_opa: COVER
            border_width: 0
            pad_all: 0""")

CORE = """        - obj:
            id: jarvis_core_outer
            align: CENTER
            x: 0
            y: 0
            width: 18
            height: 18
            radius: 120
            bg_color: ${jarvis_color}
            bg_opa: COVER
            border_width: 0
            pad_all: 0
        - obj:
            id: jarvis_core_inner
            align: CENTER
            x: 0
            y: 0
            width: 12
            height: 12
            radius: 120
            bg_color: ${jarvis_hot_color}
            bg_opa: COVER
            border_width: 0
            pad_all: 0
"""

TAIL = """
        # Same contract as every other character screen: a tap silences a
        # ringing timer, or swaps idle screens when the config defines two.
        - button:
            id: jarvis_tap
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

body = (HEAD.replace("__DRAW__", "\n".join(draw))
        + "\n".join(ticks) + "\n"
        + "\n".join(arcs) + "\n"
        + "\n".join(brackets) + "\n"
        + CORE + TAIL)
io.open(OUT, "w", encoding="utf-8", newline="\n").write(body)
print(f"{OUT}: {len(body.splitlines())} linii, {N_OUT + N_IN} lukow, {N_TICK} kresek")
