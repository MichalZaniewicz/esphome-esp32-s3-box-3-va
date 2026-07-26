"""Rysuje zrzut ekranu termostatu do base/assets/climate.png.

Off-device podglad base/screens/climate.yaml, w natywnym 320x240 i fontami
urzadzenia - jak gen_media.py i gen_weather.py, z tym samym zastrzezeniem: to
nie jest emulator LVGL, metryki tekstu roznia sie o piksel.

Kolory i jednostke czyta z pakietu. Wspolrzedne sa przepisane z jego bloku
`lvgl:`; MODES nizej udaje `hvac_modes` z encji, wiec zmiana tej listy pokazuje,
jak wiersz zachowa sie przy klimatyzacji zamiast TRV - wiersz centruje sie sam,
dokladnie tak jak na urzadzeniu.

Wymaga Pillow:  pip install pillow

Uzycie:
    python scripts/gen_climate.py
"""
import io
import os
import re
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, ".."))
PROJECT = os.path.normpath(os.path.join(REPO, ".."))
CLIMATE = os.path.join(REPO, "base", "screens", "climate.yaml")
CORE = os.path.join(REPO, "base", "core.yaml")
OUT = os.path.join(REPO, "base", "assets", "climate.png")

W, H = 320, 240
MINUS, PLUS, FIRE = "\U000F0374", "\U000F0415", "\U000F0238"

# Co pokazuje zrzut: grzeje do 21, w pokoju 19.5, tryb heat wlaczony.
TARGET, NOW, HEATING = "21°", "19.5°", True
MODES = [("Auto", False), ("Heat", True), ("Off", False)]

SUB = re.compile(r"^  ([a-z_0-9]+):\s*(.+?)\s*$")


def subs(path):
    out, inside = {}, False
    for line in io.open(path, encoding="utf-8"):
        if line.startswith("substitutions:"):
            inside = True
            continue
        if not inside:
            continue
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if not line.startswith("  "):
            break
        m = SUB.match(line)
        if m and not line.startswith("    "):
            v = m.group(2)
            if v[0] in "'\"":
                v = v[1:v.index(v[0], 1)]
            else:
                v = v.split("#")[0].strip()
            out[m.group(1)] = v
    return out


def rgb(v):
    v = v[2:] if v[:2].lower() == "0x" else v.lstrip("#")
    return tuple(int(v[i:i + 2], 16) for i in (0, 2, 4))


def font_cache():
    for base in (PROJECT, REPO, os.getcwd()):
        p = os.path.join(base, ".esphome", "font")
        if os.path.isdir(p):
            return p
    sys.exit("Brak .esphome/font - zbuduj cokolwiek raz, zeby ESPHome sciagnal fonty.")


def gfont(cache, size, weight=400):
    family = subs(CORE).get("font_family", "Figtree")
    p = os.path.join(cache, "%s@%d@False@v1.ttf" % (family, weight))
    if not os.path.exists(p):
        sys.exit("Brak fontu %s %d w %s" % (family, weight, cache))
    return ImageFont.truetype(p, size)


def icon_font(cache, size):
    for d in sorted(os.listdir(cache)):
        p = os.path.join(cache, d, "font.ttf")
        if not os.path.exists(p):
            continue
        f = ImageFont.truetype(p, size)
        bb = f.getbbox(FIRE)
        if bb and bb[2] > bb[0] and bb[3] > bb[1]:
            return f
    sys.exit("Brak webfontu Material Design Icons w %s" % cache)


def render():
    s = subs(CLIMATE)
    cache = font_cache()
    icon = icon_font(cache, 34)
    f_temp = gfont(cache, 56, 500)
    f_small = gfont(cache, 15)
    radius = int(s.get("climate_button_radius", "10"))

    im = Image.new("RGB", (W, H), rgb(s["climate_bg_color"]))
    d = ImageDraw.Draw(im)

    d.text((W // 2, 26), TARGET, font=f_temp, fill=rgb(s["climate_target_color"]), anchor="ma")
    d.text((W // 2, 96), NOW, font=f_small, fill=rgb(s["climate_now_color"]), anchor="ma")
    d.text((W // 2, 118), FIRE, font=icon, anchor="ma",
           fill=rgb(s["climate_action_color"] if HEATING else s["climate_idle_color"]))

    # Dwa duze przyciski po bokach: 68x68 na y 34.
    for x in (14, W - 14 - 68):
        d.rounded_rectangle([x, 34, x + 68, 34 + 68], radius=radius,
                            fill=rgb(s["climate_button_color"]))
    d.text((14 + 34, 34 + 34), MINUS, font=icon,
           fill=rgb(s["climate_button_icon_color"]), anchor="mm")
    d.text((W - 14 - 34, 34 + 34), PLUS, font=icon,
           fill=rgb(s["climate_button_icon_color"]), anchor="mm")

    # Wiersz trybow: 60 px na przycisk, 4 px przerwy, wysrodkowany.
    n, bw, gap = len(MODES), 60, 4
    start = (W - (n * bw + (n - 1) * gap)) // 2
    for i, (text, on) in enumerate(MODES):
        x = start + i * (bw + gap)
        d.rounded_rectangle([x, 178, x + bw, 178 + 48], radius=radius,
                            fill=rgb(s["climate_mode_on_color"] if on
                                     else s["climate_mode_color"]))
        d.text((x + bw // 2, 178 + 24), text, font=f_small, anchor="mm",
               fill=rgb(s["climate_mode_text_on_color"] if on
                        else s["climate_mode_text_color"]))

    return im


def main():
    im = render()
    im.save(OUT)
    print("zapisane: %s (%dx%d)" % (os.path.relpath(OUT, REPO), im.size[0], im.size[1]))


if __name__ == "__main__":
    main()
