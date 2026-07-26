"""Rysuje zrzut ekranu odtwarzacza do base/assets/media.png.

Off-device podglad base/screens/media.yaml, w natywnym 320x240 i fontami
urzadzenia - tak samo jak galeria stylow w README. Wspolrzedne, kolory i teksty
czyta z samego pakietu, wiec zmiana palety albo przesuniecie widgetu nie
wymaga poprawiania obrazka recznie: wystarczy uruchomic to jeszcze raz.

Czego NIE robi: nie jest emulatorem LVGL. Metryki tekstu w PIL roznia sie o
piksel, a `long_mode: DOT` jest tu przyblizony przycieciem do szerokosci pola.
Do dokumentacji to wystarcza, do sprawdzania ukladu co do piksela nie.

Fonty bierze z cache ESPHome w .esphome/font (to samo, co trafia na
urzadzenie). Ikona MDI siedzi tam pod nazwa zahaszowana od URL-a, wiec szuka
sie jej po tym, czy w ogole ma glif nutki, a nie po nazwie pliku.

Wymaga Pillow:  pip install pillow

Uzycie:
    python scripts/gen_media.py            # base/assets/media.png
    python scripts/gen_media.py --show     # dodatkowo otwiera podglad
"""
import io
import os
import re
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, ".."))
PROJECT = os.path.normpath(os.path.join(REPO, ".."))
MEDIA = os.path.join(REPO, "base", "screens", "media.yaml")
CORE = os.path.join(REPO, "base", "core.yaml")
OUT = os.path.join(REPO, "base", "assets", "media.png")

W, H = 320, 240
NOTE = "\U000F0387"
PLAY = "\U000F040A"
PAUSE = "\U000F03E4"
NEXT = "\U000F04AD"
PREV = "\U000F04AE"
VOLUME = "\U000F0580"

# Co pokazuje zrzut. Wymyslony utwor, nie cudza okladka: obrazek ma
# dokumentowac ekran, a nie czyjs album.
TITLE = "Midnight Drive"
ARTIST = "The Long Players"
ELAPSED, TOTAL, VOL = 97, 214, 20

SUB = re.compile(r"^  ([a-z_0-9]+):\s*(.+?)\s*$")


def subs(path):
    """Blok substitutions z pakietu ESPHome (ten sam parser co gen_demos)."""
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
    # NIE lstrip("0x"): to zdejmuje kazde wiodace zero i kazde x, wiec czarne
    # '0x000000' zostawialo pusty string.
    v = v[2:] if v[:2].lower() == "0x" else v.lstrip("#")
    return tuple(int(v[i:i + 2], 16) for i in (0, 2, 4))


def font_cache():
    """Katalog .esphome/font - obok configu, ktorym budujesz."""
    for base in (PROJECT, REPO, os.getcwd()):
        p = os.path.join(base, ".esphome", "font")
        if os.path.isdir(p):
            return p
    sys.exit("Brak .esphome/font - zbuduj cokolwiek raz, zeby ESPHome sciagnal fonty.")


def body_font(cache, size):
    s = subs(CORE)
    family = s.get("font_family", "Figtree")
    for name in ("%s@400@False@v1.ttf" % family, "%s@400@False.ttf" % family):
        p = os.path.join(cache, name)
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    sys.exit("Brak fontu %s w %s" % (family, cache))


def icon_font(cache, size):
    """MDI lezy pod nazwa z hasha URL-a, wiec rozpoznaje sie go po glifie."""
    for d in sorted(os.listdir(cache)):
        p = os.path.join(cache, d, "font.ttf")
        if not os.path.exists(p):
            continue
        f = ImageFont.truetype(p, size)
        bb = f.getbbox(NOTE)
        if bb and bb[2] > bb[0] and bb[3] > bb[1]:
            return f
    sys.exit("Brak webfontu Material Design Icons w %s" % cache)


def dot(draw, text, font, width):
    """`long_mode: DOT`: jedna linia, wielokropek gdy nie miesci sie w polu."""
    if draw.textlength(text, font=font) <= width:
        return text
    ell = "..."
    while text and draw.textlength(text + ell, font=font) > width:
        text = text[:-1]
    return text + ell


def cover(size, s):
    """Zastepcza okladka. Wlasna grafika, nie cudza plyta."""
    im = Image.new("RGB", (size, size), rgb(s["media_cover_bg_color"]))
    d = ImageDraw.Draw(im)
    for y in range(size):
        t = y / (size - 1.0)
        d.line([(0, y), (size, y)],
               fill=(int(18 + 30 * t), int(30 + 60 * t), int(52 + 96 * t)))
    d.ellipse([size * 0.28, size * 0.28, size * 0.72, size * 0.72],
              fill=(10, 14, 20))
    d.ellipse([size * 0.46, size * 0.46, size * 0.54, size * 0.54],
              fill=(47, 168, 224))
    return im


def rounded(im, radius):
    mask = Image.new("L", im.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, im.size[0] - 1, im.size[1] - 1],
                                           radius=radius, fill=255)
    out = Image.new("RGBA", im.size, (0, 0, 0, 0))
    out.paste(im, (0, 0), mask)
    return out


def mmss(sec):
    return "%d:%02d" % (sec // 60, sec % 60)


def render():
    s = subs(MEDIA)
    cache = font_cache()
    body = body_font(cache, 16)
    icon = icon_font(cache, 30)

    im = Image.new("RGB", (W, H), rgb(s["media_bg_color"]))
    d = ImageDraw.Draw(im)

    # Kafel okladki: obj TOP_LEFT 12,14 96x96 radius 6
    art = rounded(cover(96, s), 6)
    im.paste(art, (12, 14), art)

    # Glosnosc: label TOP_RIGHT x=-14 y=14
    vol = "%d%%" % VOL
    d.text((W - 14, 14), vol, font=body, fill=rgb(s["media_time_color"]), anchor="ra")

    # Tytul i wykonawca: TOP_LEFT x=120, y=40 i 64, szerokosc 186, jedna linia
    d.text((120, 40), dot(d, TITLE, body, 186), font=body,
           fill=rgb(s["media_title_color"]), anchor="la")
    d.text((120, 64), dot(d, ARTIST, body, 186), font=body,
           fill=rgb(s["media_artist_color"]), anchor="la")

    # Pasek: bar TOP_MID y=122, 292x6
    bx, by, bw, bh = (W - 292) // 2, 122, 292, 6
    d.rectangle([bx, by, bx + bw, by + bh], fill=rgb(s["media_bar_bg_color"]))
    d.rectangle([bx, by, bx + int(bw * ELAPSED / float(TOTAL)), by + bh],
                fill=rgb(s["media_bar_fg_color"]))

    # Czasy: TOP_LEFT x=14 y=134 i TOP_RIGHT x=-14 y=134
    d.text((14, 134), mmss(ELAPSED), font=body,
           fill=rgb(s["media_time_color"]), anchor="la")
    d.text((W - 14, 134), mmss(TOTAL), font=body,
           fill=rgb(s["media_time_color"]), anchor="ra")

    # Trzy przyciski: BOTTOM_MID y=-14, 76x56, x -80 / 0 / +80
    top = H - 14 - 56
    for dx, glyph in ((-80, PREV), (0, PAUSE), (80, NEXT)):
        cx = W // 2 + dx
        d.rounded_rectangle([cx - 38, top, cx + 38, top + 56],
                            radius=int(s["media_button_radius"]),
                            fill=rgb(s["media_button_color"]))
        d.text((cx, top + 28), glyph, font=icon,
               fill=rgb(s["media_button_icon_color"]), anchor="mm")

    return im


def main(argv):
    im = render()
    im.save(OUT)
    print("zapisane: %s (%dx%d)" % (os.path.relpath(OUT, REPO), im.size[0], im.size[1]))
    if "--show" in argv:
        im.show()


if __name__ == "__main__":
    main(sys.argv[1:])
