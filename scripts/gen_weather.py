"""Rysuje zrzut ekranu pogody do base/assets/weather.png.

Off-device podglad base/screens/weather.yaml, w natywnym 320x240 i fontami
urzadzenia - tak samo jak gen_media.py, i z tym samym zastrzezeniem: to nie
jest emulator LVGL, metryki tekstu roznia sie o piksel.

Kolory, jednostki i napisy czyta z pakietu. Wspolrzedne sa tutaj przepisane z
jego bloku `lvgl:` - jedyna rzecz, ktora trzeba poprawic recznie, jesli ekran
sie przesunie.

Dni w zrzucie jest szesc, bo tyle zwraca met.no i tyle widac na sprzecie.
Zmienna DAYS nizej przyjmie kazda liczbe do siedmiu - wiersz centruje sie sam,
dokladnie tak jak na urzadzeniu.

Wymaga Pillow:  pip install pillow

Uzycie:
    python scripts/gen_weather.py
"""
import io
import os
import re
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, ".."))
PROJECT = os.path.normpath(os.path.join(REPO, ".."))
WEATHER = os.path.join(REPO, "base", "screens", "weather.yaml")
CORE = os.path.join(REPO, "base", "core.yaml")
OUT = os.path.join(REPO, "base", "assets", "weather.png")

W, H = 320, 240

# Warunek Home Assistant -> glif MDI. Ta sama tablica co w pakiecie; jesli
# kiedys sie rozjada, zrzut pokaze co innego niz urzadzenie.
GLYPH = {
    "clear-night": "\U000F0594", "cloudy": "\U000F0590",
    "exceptional": "\U000F0F2F", "fog": "\U000F0591",
    "hail": "\U000F0592", "lightning": "\U000F0593",
    "lightning-rainy": "\U000F067E", "partlycloudy": "\U000F0595",
    "pouring": "\U000F0596", "rainy": "\U000F0597",
    "snowy": "\U000F0598", "snowy-rainy": "\U000F067F",
    "sunny": "\U000F0599", "windy": "\U000F059D",
    "windy-variant": "\U000F059E",
}

# Co pokazuje zrzut: pogoda z niczyjego konkretnego domu.
NOW = ("partlycloudy", 27, 48, 7)
DAYS = [("partlycloudy", 30, 21, "Sun"), ("rainy", 23, 16, "Mon"),
        ("partlycloudy", 25, 14, "Tue"), ("sunny", 28, 16, "Wed"),
        ("sunny", 33, 20, "Thu"), ("partlycloudy", 36, 22, "Fri")]

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
    """MDI lezy pod nazwa z hasha URL-a, wiec rozpoznaje sie go po glifie."""
    for d in sorted(os.listdir(cache)):
        p = os.path.join(cache, d, "font.ttf")
        if not os.path.exists(p):
            continue
        f = ImageFont.truetype(p, size)
        bb = f.getbbox(GLYPH["sunny"])
        if bb and bb[2] > bb[0] and bb[3] > bb[1]:
            return f
    sys.exit("Brak webfontu Material Design Icons w %s" % cache)


def render():
    s = subs(WEATHER)
    cache = font_cache()
    icon_big = icon_font(cache, 64)
    icon_small = icon_font(cache, 24)
    f_temp = gfont(cache, 44, 500)
    f_body = gfont(cache, 16)
    f_small = gfont(cache, 14)
    suffix = s.get("weather_temp_suffix", "°")

    im = Image.new("RGB", (W, H), rgb(s["weather_bg_color"]))
    d = ImageDraw.Draw(im)

    cond, temp, hum, wind = NOW
    d.text((18, 16), GLYPH[cond], font=icon_big, fill=rgb(s["weather_icon_color"]), anchor="la")
    d.text((104, 14), "%d%s" % (temp, suffix), font=f_temp,
           fill=rgb(s["weather_temp_color"]), anchor="la")
    d.text((106, 66), cond.replace("-", " ").capitalize(), font=f_body,
           fill=rgb(s["weather_cond_color"]), anchor="la")
    d.text((106, 88), "%d%%   %d %s" % (hum, wind, s.get("weather_wind_unit", "km/h")),
           font=f_small, fill=rgb(s["weather_info_color"]), anchor="la")

    d.rectangle([14, 116, 14 + 292, 116], fill=rgb(s["weather_divider_color"]))

    # Kolumny: 44 px kazda, wiersz wysrodkowany - ten sam rachunek co w pakiecie.
    n = min(len(DAYS), 7)
    start = (W - n * 44) // 2
    for i, (c, hi, lo, day) in enumerate(DAYS[:n]):
        cx = start + i * 44 + 22
        d.text((cx, 126), day, font=f_small, fill=rgb(s["weather_day_color"]), anchor="ma")
        d.text((cx, 146), GLYPH[c], font=icon_small,
               fill=rgb(s["weather_icon_color"]), anchor="ma")
        d.text((cx, 178), "%d%s" % (hi, suffix), font=f_small,
               fill=rgb(s["weather_hi_color"]), anchor="ma")
        d.text((cx, 198), "%d%s" % (lo, suffix), font=f_small,
               fill=rgb(s["weather_lo_color"]), anchor="ma")

    return im


def main():
    im = render()
    im.save(OUT)
    print("zapisane: %s (%dx%d)" % (os.path.relpath(OUT, REPO), im.size[0], im.size[1]))


if __name__ == "__main__":
    main()
