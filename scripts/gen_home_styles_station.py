"""Rysuje osiem zrzutow rodziny Station do base/assets/home-styles/.

Off-device podglad base/screens/home-styles.yaml's layout==7 (STATION), tak
samo jak gen_weather.py/gen_media.py/gen_climate.py dla swoich ekranow: nie
jest to emulator LVGL, metryki tekstu roznia sie o piksel, ale kolory,
fonty i wspolrzedne sa przepisane wprost z pakietu, nie zgadywane.

Kazdy z 8 stylow to ta sama geometria (mala godzina u gory, wielka liczba
na zewnatrz, maly pasek wewnatrz pod kreska), tylko inna paleta - dokladnie
jak w apply_home_style. Zmienne kolorow (bg/g2/grad/ck/dt/hn/cl) sa
przepisane 1:1 z tamtejszego else-if.

Wymaga Pillow:  pip install pillow

Uzycie:
    python scripts/gen_home_styles_station.py
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, ".."))
PROJECT = os.path.normpath(os.path.join(REPO, ".."))
OUT_DIR = os.path.join(REPO, "base", "assets", "home-styles")

W, H = 320, 240

CLOUD = "\U000F0590"          # weather-cloudy, font_station_icon's one glyph
THERMOMETER = "\U000F050F"
HUMIDITY = "\U000F058E"        # water-percent

# name -> (bg, g2, grad, ck, dt, hn, cl, station_aura)
# grad: 0 solid, 1 vertical (top bg -> bottom g2). Copied 1:1 from the
# else-if chain in base/screens/home-styles.yaml's apply_home_style.
STYLES = {
    "station":        (0x000000, 0x000000, 0, 0xEAF2FF, 0x3AFAE6, 0x8FA6C0, 0x8FA6C0, False),
    "station-aura":    (0x000000, 0x000000, 0, 0xFF8A5B, 0xFF8A5B, 0xFF8A5B, 0x4A3A34, True),
    "station-neon":    (0x050014, 0x050014, 0, 0x00E5FF, 0xFF3DDA, 0x6E33FF, 0x00E5FF, False),
    "station-amber":   (0x0A0500, 0x0A0500, 0, 0xFFB021, 0xB3760F, 0x7A5008, 0xFFA833, False),
    "station-fire":    (0x1A0603, 0x7A1A08, 1, 0xFFD24D, 0xFF8A3D, 0xC7663A, 0xFFB86A, False),
    "station-ice":     (0x0A1A2E, 0x2A5A8A, 1, 0xF2FAFF, 0xAFD6F0, 0x6A93B8, 0xD6ECFA, False),
    "station-forest":  (0x03140A, 0x0A3A1E, 1, 0xB8F0A8, 0x7FC77A, 0x4A7A44, 0xCDEFC0, False),
    "station-paper":   (0xEDEAE2, 0xEDEAE2, 0, 0x1A1A1A, 0x555555, 0x8A8A8A, 0x333333, False),
}

# Plausible fixed sample: not any real house's numbers, same spirit as
# gen_weather.py's NOW/DAYS.
CLOCK_TEXT = "14:32"
OUTDOOR_TEMP = "18°"
INDOOR_TEMP = "21°"
INDOOR_HUM = "48%"
OUT_LABEL, IN_LABEL, HUM_LABEL = "Outside", "Inside", "Humidity"


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
    """MDI lezy pod nazwa z hasha URL-a, wiec rozpoznaje sie go po glifie."""
    for d in sorted(os.listdir(cache)):
        p = os.path.join(cache, d, "font.ttf")
        if not os.path.exists(p):
            continue
        f = ImageFont.truetype(p, size)
        bb = f.getbbox(CLOUD)
        if bb and bb[2] > bb[0] and bb[3] > bb[1]:
            return f
    sys.exit("Brak webfontu Material Design Icons w %s" % cache)


def vgradient(im, top, bottom):
    d = ImageDraw.Draw(im)
    for y in range(H):
        t = y / (H - 1)
        row = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
        d.line([(0, y), (W, y)], fill=row)


def render(name, cache):
    bg, g2, grad, ck, dt, hn, cl, aura = STYLES[name]

    im = Image.new("RGB", (W, H), rgb(bg))
    if grad:
        vgradient(im, rgb(bg), rgb(g2))
    d = ImageDraw.Draw(im)

    f_clock = gfont(cache, 15, 400)          # font_home_small
    f_hero = gfont(cache, 56, 500)           # font_station_hero
    f_val = gfont(cache, 26, 500)            # font_station_val
    f_cloud = icon_font(cache, 52)           # font_station_icon
    f_mdi = icon_font(cache, 34)             # font_home_mdi

    # Small clock, top-centre.
    d.text((W // 2, 8), CLOCK_TEXT, font=f_clock, fill=rgb(ck), anchor="ma")

    # Outdoor hero: icon then big number, left-anchored as a pair.
    d.text((66, 38), CLOUD, font=f_cloud, fill=rgb(hn), anchor="la")
    d.text((136, 36), OUTDOOR_TEMP, font=f_hero, fill=rgb(ck), anchor="la")
    d.text((W // 2, 96), OUT_LABEL, font=f_clock, fill=rgb(cl), anchor="ma")

    # Indoor strip: icon+value pairs at x=34 (temp) and x=184 (humidity).
    icon_x = (34, 184)
    icon_glyph = (THERMOMETER, HUMIDITY)
    value = (INDOOR_TEMP, INDOOR_HUM)
    caption = (IN_LABEL, HUM_LABEL)
    for x, glyph, val, cap in zip(icon_x, icon_glyph, value, caption):
        d.text((x, 164), glyph, font=f_mdi, fill=rgb(dt), anchor="la")
        d.text((x + 28, 168), val, font=f_val, fill=rgb(ck), anchor="la")
        d.text((x - 20 + 60, 198), cap, font=f_clock, fill=rgb(cl), anchor="ma")

    if aura:
        # Nine bars frozen mid-breath, same shape as aura.yaml's idle line.
        heights = (4, 7, 10, 13, 16, 13, 10, 7, 4)
        offsets = (-40, -30, -20, -10, 0, 10, 20, 30, 40)
        cx, cy = W // 2, 120 + 16
        for dx, hgt in zip(offsets, heights):
            x0, y0 = cx + dx - 3, cy - hgt // 2
            d.rounded_rectangle([x0, y0, x0 + 6, y0 + hgt], radius=3, fill=rgb(ck))
    else:
        d.rectangle([24, 136, 24 + 272, 136], fill=rgb(hn))

    return im


def main():
    cache = font_cache()
    os.makedirs(OUT_DIR, exist_ok=True)
    for name in STYLES:
        im = render(name, cache)
        out = os.path.join(OUT_DIR, "%s.png" % name)
        im.save(out)
        print("zapisane: %s (%dx%d)" % (os.path.relpath(out, REPO), *im.size))


if __name__ == "__main__":
    main()
