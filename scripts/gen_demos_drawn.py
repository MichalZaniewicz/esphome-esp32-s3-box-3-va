"""Symulatory postaci, ktore rysuja sie same - dla scripts/gen_demos.py.

Postac z grafika to jeden obrazek plus liczby, wiec jeden renderer obsluguje
cala czternastke. Te tutaj nie maja obrazka: kazda maluje wlasna strone LVGL i
ma wlasna logike ticka, wiec kazda potrzebuje wlasnego portu tej logiki na PIL.

Zrodlem jest base/faces/<nazwa>.yaml - stamtad ida i wspolrzedne widgetow, i
wzory. Klip nie ma byc ladny, ma byc tym samym, co robi urzadzenie.

Fonty: te same pliki TTF, ktore ESPHome sciagnal przy kompilacji i trzyma w
.esphome/font/. Bez nich odwzorowanie tekstu jest zgadywaniem, a `rain` i `crt`
sa w calosci z tekstu.
"""
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, ".."))
# Cache fontow lezy przy configu, ktory kompilowal - czyli katalog wyzej niz repo.
FONTCACHE = os.path.normpath(os.path.join(REPO, "..", ".esphome", "font"))
U32 = 0xFFFFFFFF


def font(family, weight, size):
    """TTF z cache ESPHome, tak jak nazywa go integracja gfonts."""
    path = os.path.join(FONTCACHE, f"{family}@{weight}@False@v1.ttf")
    if not os.path.exists(path):
        raise SystemExit(
            f"brak fontu {path}\n"
            "Cache ESPHome go nie ma - skompiluj raz config z ta postacia, albo\n"
            "wskaz FONTCACHE na katalog, w ktorym siedzi .esphome/font.")
    return ImageFont.truetype(path, size)


def h32(n):
    """Ten sam hash, ktory licza lambdy: xor-shift razy Knuth, w 32 bitach."""
    n &= U32
    return ((n ^ (n >> 5)) * 2654435761) & U32


def rgb(s):
    s = s.lstrip("#").replace("0x", "")
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))


# ---------------------------------------------------------------------------
# rain - 12 kolumn glifow, base/faces/rain.yaml
# ---------------------------------------------------------------------------
RAIN_GLYPHS = "0123456789ABCDEF<>|/=+*-"
RAIN_X = [6 + 26 * c for c in range(12)]
RAIN_LINE = 20          # 16 px fontu + 4 px odstepu = dokladnie 12 wierszy na 240


def rain_columns(phase, f):
    tail, speed = 5, 1
    head, mid, dim = "7CFFA8", "2EA85E", "103A22"
    frozen = sync = False
    if phase == "listening":
        tail, speed, frozen, head = 7, 2, True, "D8FFE8"
    elif phase == "thinking":
        tail, speed = 11, 3
    elif phase == "replying":
        tail, speed, sync = 8, 2, True
        head, mid = "A8F0FF", "2E8AA8"
    elif phase in ("timer", "error"):
        tail, speed = 11, 3
        head = mid = "FF4D4D"
        dim = "2E4A38"
    elif phase == "muted":
        head = mid = dim = "2E4A38"

    band = int((f * 3 / 2) % 12) if phase == "replying" else -1
    churn = f if frozen else f // 3
    out = []
    for c in range(12):
        # W idle pada tylko czesc kolumn - stad drizzle zamiast wolniejszej ulewy.
        if phase == "idle" and (c * 5) % 12 >= 5:
            out.append([])
            continue
        drift = 0 if frozen else f * speed
        offset = 0 if sync else (h32(c * 151) >> 16) & 0x3F
        lead = ((drift + offset) // 2) % (12 + tail)
        rows = []
        for r in range(12):
            dist = lead - r
            on_band = r == band
            if not on_band and (dist < 0 or dist > tail):
                continue
            col = head if (on_band or dist == 0) else (mid if dist <= 2 else dim)
            g = h32(churn * 31 + r * 7 + c * 101)
            rows.append((r, col, RAIN_GLYPHS[((g >> 16) + r) % len(RAIN_GLYPHS)]))
        out.append(rows)
    return out


def rain_frame(s, phase, f, pf=0):
    im = Image.new("RGB", (320, 240), (0, 0, 0))
    d = ImageDraw.Draw(im)
    ft = font("Roboto Mono", 500, 16)
    for c, rows in enumerate(rain_columns(phase, f)):
        for r, col, ch in rows:
            d.text((RAIN_X[c], r * RAIN_LINE), ch, font=ft, fill=rgb(col))
    return im


# ---------------------------------------------------------------------------
# crt - zielony terminal, base/faces/crt.yaml
# ---------------------------------------------------------------------------
CRT_BG = rgb("041208")
CRT_BRIGHT = "5CF58A"
CRT_DIM = "1E6B38"
CRT_HEAD = "9BFFB8"
CRT_ALARM = "FF8080"
CRT_RULE = rgb("1E6B38")
CRT_SCAN = rgb("0A2415")
CRT_COLS, CRT_ROWS = 32, 6
CRT_LINE = 23           # 15 px fontu + 8 px odstepu
# Co terminal ma na sobie napisane w klipie. Na urzadzeniu to jest to, co
# naprawde padlo - tu musi byc cokolwiek, inaczej `thinking` i `replying`
# pokazuja pusty ekran i nie widac tego, co ta postac ma najciekawszego.
# Te dwa zdania sa te same, co w poprzednim klipie, zeby zmiana byla widoczna
# tylko tam, gdzie miala byc.
CRT_REQUEST = "set a timer for twelve minutes"
CRT_RESPONSE = "Twelve minute timer, starting now."


def crt_wrap(src, colour, out, limit):
    cap = len(out) + limit
    i = 0
    while i < len(src) and len(out) < CRT_ROWS and len(out) < cap:
        take = CRT_COLS
        if i + take < len(src):
            sp = src.rfind(" ", 0, i + take + 1)
            if sp != -1 and sp > i + CRT_COLS // 2:
                take = sp - i
        out.append((colour, src[i:i + take]))
        i += take
        while i < len(src) and src[i] == " ":
            i += 1


def crt_lines(s, phase, f, pf):
    lines = []
    if phase == "listening":
        span = CRT_COLS - 4
        n = 1 + (pf * 3 // 5) % span
        lines.append((CRT_BRIGHT, "> " + "=" * n))
        lines.append((CRT_DIM, "  " + s["crt_listen_label"]))
    elif phase == "thinking":
        crt_wrap("> " + CRT_REQUEST, CRT_DIM, lines, 2)
        lines.append((CRT_BRIGHT, s["crt_think_text"] + "." * (1 + (pf // 3) % 4)))
    elif phase == "replying":
        crt_wrap("> " + CRT_REQUEST, CRT_DIM, lines, 2)
        shown = pf * 2
        part = CRT_RESPONSE if shown >= len(CRT_RESPONSE) else CRT_RESPONSE[:shown]
        if part:
            crt_wrap(part, CRT_BRIGHT, lines, CRT_ROWS)
    elif phase == "timer":
        if f % 6 < 3:
            lines.append((CRT_ALARM, s["crt_timer_text"]))
    elif phase == "error":
        lines.append((CRT_ALARM, s["crt_error_text"]))
    elif phase == "muted":
        lines.append((CRT_DIM, s["crt_muted_text"]))
    else:
        lines.append((CRT_BRIGHT, "> " + ("_" if f % 10 < 5 else "")))
        while len(lines) < CRT_ROWS - 1:
            lines.append(None)
        lines.append((CRT_DIM, s["crt_idle_hint"]))
    return lines[:CRT_ROWS]


def crt_frame(s, phase, f, pf=None):
    if pf is None:
        pf = f
    im = Image.new("RGB", (320, 240), CRT_BG)
    d = ImageDraw.Draw(im)
    ft = font("Roboto Mono", 400, 15)
    d.text((14, 10), s["crt_header"], font=ft, fill=rgb(CRT_HEAD))
    d.rectangle((12, 32, 12 + 295, 32), fill=CRT_RULE)
    for i, line in enumerate(crt_lines(s, phase, f, pf)):
        if line is None:
            continue
        colour, text = line
        d.text((14, 44 + i * CRT_LINE), " " + text, font=ft, fill=rgb(colour))
    # Linie skanowania sa NA WIERZCHU tekstu, jak na urzadzeniu - to one robia
    # z tego kineskop, a nie tlo.
    for y in range(0, 240, 8):
        d.rectangle((0, y, 319, y), fill=CRT_SCAN)
    return im


DRAWN = {
    "rain": rain_frame,
    "crt": crt_frame,
}
