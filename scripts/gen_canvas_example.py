"""Rysuje przykladowy zrzut base/screens/canvas.yaml do
base/assets/canvas-example.png - dokladnie ten sam spec, ktory README i
wiki juz drukuja jako kod (wykres slupkowy), zeby obok tekstu bylo widac
efekt.

Off-device podglad, tak samo jak gen_weather.py/gen_media.py/gen_climate.py:
nie jest to emulator LVGL, ale parsuje TEN SAM format co canvas_draw
(rect/circle/text/icon, pipe-separated) wiec dowolny inny spec z dokumentacji
przejdzie przez ten sam kod bez zmian - patrz SPEC nizej.

Wymaga Pillow:  pip install pillow

Uzycie:
    python scripts/gen_canvas_example.py
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, ".."))
PROJECT = os.path.normpath(os.path.join(REPO, ".."))
OUT = os.path.join(REPO, "base", "assets", "canvas-example.png")

W, H = 320, 240
BG = 0x000000

# The exact bar-chart example already printed in README.md and wiki's
# Configuration.md - keep those three in sync if this ever changes.
SPEC = ("rect,20,140,20,60,0,FF8A3D|rect,50,120,20,80,0,FF8A3D|"
        "rect,80,90,20,110,0,FF8A3D|text,20,205,0,8FA6C0,6|"
        "text,50,205,0,8FA6C0,12|text,80,205,0,8FA6C0,18")

# Same 20-name list as canvas.yaml's ICONS[] table.
ICON_GLYPH = {
    "sun": "\U000F0599", "cloud": "\U000F0590", "partly-cloudy": "\U000F0595",
    "rain": "\U000F0597", "pouring": "\U000F0596", "snow": "\U000F0598",
    "snow-rain": "\U000F067F", "fog": "\U000F0591", "hail": "\U000F0592",
    "lightning": "\U000F0593", "storm": "\U000F067E", "wind": "\U000F059D",
    "wind2": "\U000F059E", "night": "\U000F0594", "alert": "\U000F0F2F",
    "thermometer": "\U000F050F", "humidity": "\U000F058E", "fire": "\U000F0238",
    "minus": "\U000F0374", "plus": "\U000F0415",
}


def rgb(v):
    return ((v >> 16) & 0xFF, (v >> 8) & 0xFF, v & 0xFF)


def font_cache():
    for base in (PROJECT, REPO, os.getcwd()):
        p = os.path.join(base, ".esphome", "font")
        if os.path.isdir(p):
            return p
    sys.exit("Brak .esphome/font - zbuduj cokolwiek raz, zeby ESPHome sciagnal fonty.")


def gfont(cache, size, weight=400, family="Figtree"):
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
        bb = f.getbbox(ICON_GLYPH["sun"])
        if bb and bb[2] > bb[0] and bb[3] > bb[1]:
            return f
    sys.exit("Brak webfontu Material Design Icons w %s" % cache)


def render(spec, cache):
    im = Image.new("RGB", (W, H), rgb(BG))
    d = ImageDraw.Draw(im)

    f_body = gfont(cache, 16, 400)        # SIZE 0 text - font_body
    f_med = gfont(cache, 24, 400)         # SIZE 1 text - font_canvas_med
    f_lg = gfont(cache, 40, 500)          # SIZE 2 text - font_canvas_lg
    f_icon_s = icon_font(cache, 24)       # SIZE 0 icon
    f_icon_l = icon_font(cache, 48)       # SIZE 1+ icon
    text_font = (f_body, f_med, f_lg)

    for item in spec.split("|"):
        if not item.strip():
            continue
        fields = item.split(",")
        kind = fields[0]
        if kind == "rect":
            _, x, y, w, h, r, col = fields
            x, y, w, h = int(x), int(y), int(w), int(h)
            d.rounded_rectangle([x, y, x + max(w, 1), y + max(h, 1)],
                                 radius=int(r), fill=rgb(int(col, 16)))
        elif kind == "circle":
            _, cx, cy, rad, col = fields
            cx, cy, rad = int(cx), int(cy), int(rad)
            d.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], fill=rgb(int(col, 16)))
        elif kind == "text":
            x, y, sz, col = fields[1], fields[2], fields[3], fields[4]
            label = ",".join(fields[5:])
            f = text_font[min(int(sz), 2)]
            d.text((int(x), int(y)), label, font=f, fill=rgb(int(col, 16)), anchor="la")
        elif kind == "icon":
            x, y, sz, col = fields[1], fields[2], fields[3], fields[4]
            name = ",".join(fields[5:])
            f = f_icon_l if int(sz) >= 1 else f_icon_s
            glyph = ICON_GLYPH.get(name, ICON_GLYPH["alert"])
            d.text((int(x), int(y)), glyph, font=f, fill=rgb(int(col, 16)), anchor="la")

    return im


def main():
    cache = font_cache()
    im = render(SPEC, cache)
    im.save(OUT)
    print("zapisane: %s (%dx%d)" % (os.path.relpath(OUT, REPO), *im.size))


if __name__ == "__main__":
    main()
