"""Generuje base/faces/nixie.yaml - cztery lampy cyfrowe."""
import os

# Sciezka liczona wzgledem tego pliku, nie zaszyta na sztywno. Generatory zyly
# do 2026-07-20 w katalogu tymczasowym z absolutna sciezka do jednego dysku:
# nie dalo sie ich uruchomic nigdzie indziej, a skasowanie katalogu skasowaloby
# jedyne zrodlo tych plikow.
_FACES = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "base", "faces")
)
import io

OUT = os.path.join(_FACES, "nixie.yaml")
CX, CY = 160, 120
TUBES = (56, 116, 204, 264)
DW, DH, T = 26, 44, 5          # szerokosc, wysokosc, grubosc segmentu

# Segmenty cyfry siedmiosegmentowej, wzgledem srodka lampy.
SEGS = {
    "a": (-DW // 2, -DH // 2, DW, T),
    "b": (DW // 2 - T, -DH // 2, T, DH // 2),
    "c": (DW // 2 - T, 0, T, DH // 2),
    "d": (-DW // 2, DH // 2 - T, DW, T),
    "e": (-DW // 2, 0, T, DH // 2),
    "f": (-DW // 2, -DH // 2, T, DH // 2),
    "g": (-DW // 2, -T // 2, DW, T),
}
ORDER = "abcdefg"
DIGIT = {0: "abcdef", 1: "bc", 2: "abged", 3: "abgcd", 4: "fgbc",
         5: "afgcd", 6: "afgedc", 7: "abc", 8: "abcdefg", 9: "abfgcd"}

HEAD = """###############################################################################
# Nixie - four glass tubes with glowing digits.
#
# No artwork: four tube bodies, four glow pools and twenty eight segments, all
# LVGL objects. Like the other drawn characters it does NOT nest
# base/screens/face.yaml.
#
# THE ONLY CHARACTER THAT IS USEFUL WHILE IDLE. Every other assistant here looks
# good doing nothing; this one shows the clock, read from the core's `ha_time`.
# That is worth knowing when choosing: on a kitchen shelf it earns its screen.
#
# While replying the glow TRAVELS across the tubes rather than pulsing in all
# four at once. That was a deliberate second attempt: an even pulse gave the eye
# nothing to follow and read as flicker, and when the wave was allowed to run
# past the end tubes they all went dark together, which read as a fault. The
# wave now circles, and the tubes never go out - it adds glow on top of a floor.
#
# Colours are written straight through the LVGL C API from one lambda, and only
# for the objects whose value actually changed. Thirty four YAML actions per
# tick would repaint the whole panel whether or not anything moved.
###############################################################################

substitutions:
  nixie_on_color: '0xFF8A1E'      # the glow at rest
  nixie_hot_color: '0xFFC87A'     # the crest of the travelling wave
  nixie_off_color: '0x2E1C10'     # an unlit segment still shows: it is a filament
  nixie_glass_color: '0x1C1612'
  nixie_pool_color: '0x3A1E0C'    # the haze inside the glass behind a lit digit
  nixie_alarm_color: '0xFF5A3C'
  nixie_muted_color: '0x3A2A20'
  nixie_bg_color: '0x0A0705'

  nixie_wave_speed: '55'          # hundredths of a tube per tick, while replying
  nixie_wave_floor: '85'          # glow every tube keeps, hundredths
  nixie_wave_peak: '85'           # what the crest adds on top, hundredths

  nixie_tick: 100ms

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
  - id: nixie_frame
    type: int
    restore_value: false
    initial_value: "0"

esphome:
  on_boot:
    - priority: 800
      then:
        - logger.log:
            level: INFO
            format: "package: faces/nixie.yaml (nixie tubes, no artwork)"

script:
  - id: nixie_tick_script
    mode: single
    then:
      - lambda: |-
          static lv_obj_t *seg[28] = {
__SEGPTRS__
          };
          static lv_obj_t *pool[4] = {id(nx_pool_0), id(nx_pool_1), id(nx_pool_2), id(nx_pool_3)};
          static lv_obj_t *colon[2] = {id(nx_colon_top), id(nx_colon_bot)};
          // Which digit lights which segments, in order a b c d e f g.
          static const uint8_t MAP[10] = {
            0b1111110, 0b0110000, 0b1101101, 0b1111001, 0b0110011,
            0b1011011, 0b1011111, 0b1110000, 0b1111111, 0b1111011
          };
          static uint8_t seen[34];
          static bool primed = false;

          // Wrapped, not free-running: at ~10^7 the float product in sinf() loses
          // enough precision that the breath turns into a stepped wobble. The
          // period is a multiple of every cycle this file uses.
          const int f = id(nixie_frame);
          id(nixie_frame) = (f + 1) % 36000;
          const int phase = id(voice_assistant_phase);

          // --- what the tubes should read -----------------------------------
          int d[4];
          auto now = id(ha_time).now();
          const int hh = now.is_valid() ? now.hour : 0;
          const int mm = now.is_valid() ? now.minute : 0;
          d[0] = hh / 10; d[1] = hh % 10; d[2] = mm / 10; d[3] = mm % 10;

          int glow[4] = {255, 255, 255, 255};
          bool colon_on = true;

          auto rnd = [](int a, int b) {
            uint32_t n = (uint32_t) (a * 73 + b * 151);
            n = (n ^ (n >> 5)) * 2654435761u;
            return (int) ((n >> 16) & 0xFF);
          };

          if (phase == ${voice_assist_listening_phase_id}) {
            for (int i = 0; i < 4; i++) { d[i] = rnd(f, i) % 10; glow[i] = 255; }
          } else if (phase == ${voice_assist_thinking_phase_id}) {
            for (int i = 0; i < 4; i++) { d[i] = rnd(f / 2, i * 7) % 10; glow[i] = 190; }
          } else if (phase == ${voice_assist_replying_phase_id}) {
            // The crest circles the four tubes; distance is measured the short
            // way round so it never leaves the panel dark.
            const float head = fmodf(f * ${nixie_wave_speed} / 100.0f, 4.0f);
            for (int i = 0; i < 4; i++) {
              float dist = fabsf(i - head);
              if (dist > 2.0f) dist = 4.0f - dist;
              const float crest = dist < 1.25f ? (1.0f - dist * 0.8f) : 0.0f;
              glow[i] = (int) (${nixie_wave_floor} * 2.55f + ${nixie_wave_peak} * 2.55f * crest);
              if (dist < 0.6f) d[i] = rnd(f, i * 3) % 10;
            }
          } else if (phase == ${voice_assist_timer_finished_phase_id} ||
                     phase == ${voice_assist_error_phase_id}) {
            for (int i = 0; i < 4; i++) { d[i] = 0; glow[i] = (f % 2) ? 255 : 60; }
          } else if (phase == ${voice_assist_muted_phase_id}) {
            for (int i = 0; i < 4; i++) glow[i] = 70;
          } else {
            // Quantised to steps of 8, same reason as gen_pixel.py: a smooth
            // breath changes every lit segment on well over half the ticks, and
            // idle is the state this thing sits in almost permanently. The paint
            // step below halves it into `base/2 + 1`, so a step of 8 lands as 4
            // out of 255 on screen - under 2% of brightness, invisible - while
            // cutting the writes that reach LVGL by roughly five.
            const int breath = ((235 + (int) (20.0f * sinf(f * 0.09f))) / 8) * 8;
            for (int i = 0; i < 4; i++) glow[i] = breath;
            colon_on = (f % 10) < 5;      // only the idle clock ticks
          }

          // --- paint ---------------------------------------------------------
          uint32_t lit = ${nixie_on_color};
          const uint32_t hot = ${nixie_hot_color};
          const uint32_t off = ${nixie_off_color};
          if (phase == ${voice_assist_timer_finished_phase_id} ||
              phase == ${voice_assist_error_phase_id}) lit = ${nixie_alarm_color};
          else if (phase == ${voice_assist_muted_phase_id}) lit = ${nixie_muted_color};

          // The skip-if-unchanged cache is keyed on BRIGHTNESS, which does not
          // capture a change of colour. Going idle -> muted on a tick where the
          // colon happened to be lit left it full orange next to four correctly
          // dimmed tubes, for the whole muted phase. Force a repaint whenever
          // the lit colour itself moves.
          static uint32_t painted = 0;
          const bool recolour = (painted != lit);
          painted = lit;

          // Blends PACKED COLOURS and returns one, so the calls can nest:
          // the crest is a blend applied on top of a blend. Returning
          // lv_color_t here instead makes the nested call a type error.
          auto blend = [](uint32_t a, uint32_t b, int t) -> uint32_t {
            const int r = (int) ((a >> 16) & 0xFF) + (((int) ((b >> 16) & 0xFF) - (int) ((a >> 16) & 0xFF)) * t) / 255;
            const int g = (int) ((a >> 8) & 0xFF) + (((int) ((b >> 8) & 0xFF) - (int) ((a >> 8) & 0xFF)) * t) / 255;
            const int bl = (int) (a & 0xFF) + (((int) (b & 0xFF) - (int) (a & 0xFF)) * t) / 255;
            return ((uint32_t) r << 16) | ((uint32_t) g << 8) | (uint32_t) bl;
          };

          for (int i = 0; i < 4; i++) {
            const int g = glow[i];
            const int base = g > 255 ? 255 : g;
            const int over = g > 255 ? (g - 255 > 255 ? 255 : g - 255) : 0;
            for (int s = 0; s < 7; s++) {
              const bool on = (MAP[d[i]] >> (6 - s)) & 1;
              const uint8_t want = on ? (uint8_t) (base / 2 + over / 2 + 1) : 0;
              const int idx = i * 7 + s;
              if (primed && !recolour && seen[idx] == want) continue;
              seen[idx] = want;
              lv_obj_set_style_bg_color(seg[idx],
                  lv_color_hex(on ? blend(blend(off, lit, base), hot, over) : off), 0);
            }
            const uint8_t pw = (uint8_t) (base / 2 + 1);
            if (!primed || recolour || seen[28 + i] != pw) {
              seen[28 + i] = pw;
              lv_obj_set_style_bg_color(pool[i],
                  lv_color_hex(blend(${nixie_glass_color}, ${nixie_pool_color}, base)), 0);
            }
          }
          const uint8_t cw = colon_on ? 1 : 0;
          if (!primed || recolour || seen[32] != cw) {
            seen[32] = cw;
            for (int k = 0; k < 2; k++)
              lv_obj_set_style_bg_color(colon[k],
                  colon_on ? lv_color_hex(lit) : lv_color_hex(off), 0);
          }
          primed = true;

interval:
  - interval: ${nixie_tick}
    then:
      - if:
          condition:
            lvgl.page.is_showing: page_face
          then:
            - script.execute: nixie_tick_script

lvgl:
  pages:
    - id: page_face
      bg_color: ${nixie_bg_color}
      # No scrollbar. These pages are drawn to fill the screen and there is
      # nothing to scroll to, but content sized to exactly 240 px renders a hair
      # taller than the arithmetic says and LVGL then draws a bar down the right
      # hand side. Seen on `rain` on hardware 2026-07-22; every page here is the
      # same shape of risk, and turning it off costs nothing.
      scrollbar_mode: "OFF"
      widgets:
"""

TAIL = """
        # Same contract as every other character screen: a tap silences a
        # ringing timer, or swaps idle screens when the config defines two.
        - button:
            id: nixie_tap
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


def obj(wid, x, y, w, h, radius, color, comment=None):
    c = f"            # {comment}\n" if comment else ""
    return f"""        - obj:
{c}            id: {wid}
            align: CENTER
            x: {x}
            y: {y}
            width: {w}
            height: {h}
            radius: {radius}
            bg_color: {color}
            bg_opa: COVER
            border_width: 0
            pad_all: 0"""


widgets, ptrs = [], []
for i, tx in enumerate(TUBES):
    dx = tx - CX
    widgets.append(obj(f"nx_glass_{i}", dx, 0, 52, 92, 24, "${nixie_glass_color}",
                       "the tube body" if i == 0 else None))
    widgets.append(obj(f"nx_pool_{i}", dx, 0, 40, 80, 20, "${nixie_glass_color}",
                       "haze behind the digit; brightens with the glow" if i == 0 else None))
for i, tx in enumerate(TUBES):
    for s in ORDER:
        lx, ly, w, h = SEGS[s]
        x = tx + lx + w // 2 - CX
        y = ly + h // 2
        widgets.append(obj(f"nx_seg_{i}_{s}", x, y, w, h, 2, "${nixie_off_color}"))
        ptrs.append(f"id(nx_seg_{i}_{s})")
for k, dy in ((("top"), -16), (("bot"), 16)):
    widgets.append(obj(f"nx_colon_{k}", 0, dy, 10, 10, 5, "${nixie_off_color}"))

seg_lines = []
for i in range(0, len(ptrs), 7):
    seg_lines.append("            " + ", ".join(ptrs[i:i + 7]) + ",")

body = HEAD.replace("__SEGPTRS__", "\n".join(seg_lines)) + "\n".join(widgets) + "\n" + TAIL
io.open(OUT, "w", encoding="utf-8", newline="\n").write(body)
print(f"{OUT}: {len(body.splitlines())} linii, {len(widgets)} widgetow")
