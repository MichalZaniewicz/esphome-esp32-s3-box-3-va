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
import math
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


# ---------------------------------------------------------------------------
# Wspolne: widget LVGL wysrodkowany na ekranie, jak `align: CENTER` + x/y
# ---------------------------------------------------------------------------
def box(d, x, y, w, h, r, colour):
    """Prostokat o srodku w (160+x, 120+y). LVGL przycina promien do polowy
    krotszego boku - stad min() - i to jest to, co robi z kwadratu kolo."""
    r = max(0, min(int(r), w // 2, h // 2))
    d.rounded_rectangle((160 + x - w / 2, 120 + y - h / 2,
                         160 + x - w / 2 + w - 1, 120 + y - h / 2 + h - 1),
                        radius=r, fill=colour)


def mix(off, lit, v):
    """Kolor segmentu: liniowo miedzy zgaszonym a zapalonym, v to 0..255.
    Tak samo licza to lambdy - skladowa po skladowej, nie przez jasnosc."""
    o, l = rgb(off), rgb(lit)
    return tuple(o[i] + (l[i] - o[i]) * v // 255 for i in range(3))


# ---------------------------------------------------------------------------
# aura - dziewiec slupkow, base/faces/aura.yaml
# ---------------------------------------------------------------------------
def aura_frame(s, phase, f, pf=0):
    REST, MAXH = 4, 84
    colour = {"timer": "FF4D4D", "error": "FF4D4D",
              "muted": "4A3A34"}.get(phase, "FF8A5B")
    im = Image.new("RGB", (320, 240), (0, 0, 0))
    d = ImageDraw.Draw(im)
    for i in range(9):
        dd = i - 4
        edge = 4 - abs(dd)
        if phase == "listening":
            w = math.sin((f * 0.22) - abs(dd) * 0.6)
            h = REST + int((0.35 + 0.35 * w) * MAXH * (0.35 + 0.16 * edge))
        elif phase == "thinking":
            span = 16
            p = f % (span * 2)
            if p >= span:
                p = span * 2 - p
            pos = (p * 8) // span
            dist = abs(pos - i)
            h = REST + ((MAXH // 3) >> dist if dist <= 1 else 0)
        elif phase == "replying":
            amp = (h32(f * 73 + i * 151) >> 16) & 0xFF
            h = REST + (amp * MAXH * (2 + edge)) // (255 * 8)
        elif phase == "timer":
            h = REST + (MAXH * 2 // 3 if (f + i) % 2 else MAXH // 3)
        elif phase in ("muted", "error"):
            h = REST
        else:
            w = math.sin(f * 0.16 - i * 0.35)
            h = REST + int((1.0 + w) * 9 / 2.0)
        box(d, -72 + 18 * i, 0, 16, max(h, REST), 8, rgb(colour))
    return im


# ---------------------------------------------------------------------------
# bit - dwoje oczu i usta na czerni, base/faces/bit.yaml
# ---------------------------------------------------------------------------
def bit_frame(s, phase, f, pf=0):
    ew, eh, gx, mw, mh, pup = 54, 66, 0, 46, 8, True
    if phase == "listening":
        ew, eh, mw, mh = ew + 6, eh + 14, 26, 26
    elif phase == "thinking":
        gx = -14 if (f % 40) < 20 else 14
        ew, eh, mw, mh = ew - 4, 36, 14, 14
    elif phase == "replying":
        amp = (h32(f * 73 + 151) >> 16) & 0xFF
        eh, mw, mh = eh - 8, 40, 8 + (amp * 42) // 255
    elif phase in ("timer", "error"):
        mw, mh = 52, 40
    elif phase == "muted":
        eh, mw, mh, pup = 6, 46, 8, False
    else:
        t = f % 100
        if t in (0, 1, 5, 6):
            eh, pup = 6, False
        elif 30 <= t < 40:
            gx = -14
        elif 50 <= t < 60:
            gx = 14

    # Zrenica musi zmiescic sie w oku RAZEM z odchyleniem wzroku.
    pw = min(20, ew - 14)
    ph = min(20, eh - 10)
    if pw < 4 or ph < 4:
        pup = False
    lim = max((ew - pw) // 2 - 2, 0)
    gx = max(-lim, min(lim, gx))

    colour = {"timer": "FF4D4D", "error": "FF4D4D",
              "muted": "2E3D49"}.get(phase, "8FD4FF")
    im = Image.new("RGB", (320, 240), (0, 0, 0))
    d = ImageDraw.Draw(im)
    for sign in (-1, 1):
        box(d, sign * 62, -18, ew, eh, 26, rgb(colour))
    if pup:
        for sign in (-1, 1):
            box(d, sign * 62 + gx, -18, pw, ph, 10, rgb("122A3D"))
    box(d, 0, 48, mw, mh, 10, rgb(colour))
    return im


# ---------------------------------------------------------------------------
# iris - jedno oko na caly ekran, base/faces/iris.yaml
# ---------------------------------------------------------------------------
def iris_frame(s, phase, f, pf=0):
    ir, pr, dx, lid = 70, 28, 0, 0
    if phase == "listening":
        ir, pr = 74, 34 + int(3.0 * math.sin(f * 0.30))
    elif phase == "thinking":
        ir, pr, lid = 66, 16, 14
        dx = -26 if (f % 30) < 15 else 26
    elif phase == "replying":
        amp = (h32(f * 73 + 151) >> 16) & 0xFF
        ir, pr = 70 + (amp * 10) // 255, 28 + (amp * 8) // 255
    elif phase in ("timer", "error"):
        ir, pr = 74, 34
    elif phase == "muted":
        lid = 96
    else:
        t = f % 100
        if t in (0, 1, 6, 7):
            lid = 96
        elif t in (2, 5):
            lid = 48
        dx = (int(14 * math.sin(f * 0.06)) // 3) * 3

    pr = max(6, min(pr, ir - 12 - 6))
    alarm = {"timer": "FF4D4D", "error": "FF4D4D", "muted": "2E3D49"}.get(phase)
    im = Image.new("RGB", (320, 240), (0, 0, 0))
    d = ImageDraw.Draw(im)
    box(d, 0, 0, 308, 148, 96, rgb("121824"))
    box(d, dx, 0, ir * 2, ir * 2, 120, rgb(alarm or "1B6E8A"))
    box(d, dx, 0, (ir - 12) * 2, (ir - 12) * 2, 120, rgb(alarm or "3FC1E0"))
    box(d, dx, 0, pr * 2, pr * 2, 120, rgb("04080C"))
    box(d, dx - ir // 2, -34, 22, 22, 120, rgb("FFFFFF"))
    # Powieki: pelna szerokosc, przy gorze i dole ekranu, czarne jak tlo.
    d.rectangle((0, 0, 319, 46 + lid - 1), fill=(0, 0, 0))
    d.rectangle((0, 240 - (46 + lid), 319, 239), fill=(0, 0, 0))
    return im


# ---------------------------------------------------------------------------
# kitt - dziewiec segmentow miedzy szynami, base/faces/kitt.yaml
# ---------------------------------------------------------------------------
def kitt_frame(s, phase, f, pf=0):
    SPAN = 8.0
    lit = "FF2A18"
    if phase in ("timer", "error"):
        lit = "FFB030"
    elif phase == "muted":
        lit = "3A2A28"

    im = Image.new("RGB", (320, 240), rgb("08080A"))
    d = ImageDraw.Draw(im)
    for sign in (-1, 1):
        y = 120 + sign * 40
        d.rectangle((0, y - 2, 319, y + 1), fill=rgb("7A808C"))
    for i in range(9):
        if phase == "listening":
            w = math.fmod(f * 0.30, SPAN / 2.0 + 1.0)
            dd = abs(i - SPAN / 2.0)
            v = max(int(255.0 * (1.0 - abs(dd - w) * 0.75)), 30)
        elif phase == "thinking":
            p = math.fmod(f * 90 / 100.0, SPAN * 2.0)
            pos = p if p < SPAN else SPAN * 2.0 - p
            v = max(int(255.0 * (1.0 - abs(i - pos) * 85 / 100.0)), 20)
        elif phase == "replying":
            v = 38 + ((h32(f * 73 + i * 151) >> 16) & 0xFF) * 217 // 255
        elif phase in ("timer", "error"):
            v = 255 if (f // 2) % 2 else 30
        elif phase == "muted":
            v = 26
        else:
            p = math.fmod(f * 28 / 100.0, SPAN * 2.0)
            pos = p if p < SPAN else SPAN * 2.0 - p
            v = max(int(255.0 * (1.0 - abs(i - pos) * 55 / 100.0)), 15)
        box(d, -128 + 32 * i, 0, 26, 46, 4, mix("2A0806", lit, max(0, min(255, v))))
    return im


# ---------------------------------------------------------------------------
# pixel - matryca 12x8 diod, base/faces/pixel.yaml
# ---------------------------------------------------------------------------
PX_RING = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 23, 35, 47, 59, 71, 83, 95, 94,
           93, 92, 91, 90, 89, 88, 87, 86, 85, 84, 72, 60, 48, 36, 24, 12]


def pixel_frame(s, phase, f, pf=0):
    want = [0] * 96

    def put(r, c, v):
        # Jasniejsze zadanie wygrywa, zeby fala przechodzaca przez twarz jej
        # nie gasila.
        if 0 <= r < 8 and 0 <= c < 12 and v > want[r * 12 + c]:
            want[r * 12 + c] = v

    gaze, blink, squint, draw_face = 0, False, False, True
    idle_t = f % 100
    if phase == "thinking":
        squint = True
        gaze = -1 if (f % 40) < 20 else 1
    elif phase == "muted":
        blink = True
    elif phase in ("timer", "error"):
        draw_face = False
    elif phase == "idle":
        blink = idle_t in (0, 1, 5, 6)
        if 30 <= idle_t < 40:
            gaze = -1
        elif 50 <= idle_t < 60:
            gaze = 1

    if draw_face:
        eye_l, eye_r = (2, 3, 4), (7, 8, 9)
        if blink:
            for k in range(3):
                put(3, eye_l[k], 255)
                put(3, eye_r[k], 255)
        else:
            for rr in range(2 if squint else 1, 4):
                for k in range(3):
                    put(rr, eye_l[k], 255)
                    put(rr, eye_r[k], 255)
            # Zrenica przypisana, nie przez put(): ma PRZYGASIC zapalona diode.
            pr = 3 if squint else 2
            want[pr * 12 + (3 + gaze)] = 30
            want[pr * 12 + (8 + gaze)] = 30

    if phase == "listening":
        for rr in (5, 6):
            for cc in range(4, 8):
                put(rr, cc, 255)
        wave = math.fmod(f * 0.45, 8.0)
        for rr in range(8):
            for cc in range(12):
                dx, dy = (cc - 5.5) * 0.55, rr - 3.0
                if abs(math.sqrt(dx * dx + dy * dy) - wave) < 0.9:
                    put(rr, cc, 76)
    elif phase == "thinking":
        put(6, 5, 217)
        put(6, 6, 217)
        tail = (255, 140, 76, 38)
        for k in range(4):
            idx = PX_RING[((f * 2 - k) % 36 + 36) % 36]
            want[idx] = max(want[idx], tail[k])
    elif phase == "replying":
        amp = (h32(f * 73 + 151) >> 16) & 0xFF
        rows_open = 1 + amp * 3 // 256
        half = 3 if amp > 140 else 2
        for rr in range(5, 5 + rows_open):
            for cc in range(6 - half, 6 + half):
                put(rr, cc, 255)
    elif phase in ("timer", "error"):
        for rr in range(8):
            for cc in range(12):
                put(rr, cc, 255 if (rr + cc + f // 2) % 2 else 51)
    elif phase == "muted":
        for cc in range(3, 9):
            put(6, cc, 255)
    else:
        for cc in range(3, 9):
            put(6, cc, 255)
        put(5, 2, 255)
        put(5, 9, 255)
        breath = ((26 + int(15.0 * math.sin(f * 0.08))) // 8) * 8
        for i in range(96):
            want[i] = max(want[i], breath)

    lit = "4CFF7A"
    if phase in ("timer", "error"):
        lit = "FF4D4D"
    elif phase == "muted":
        lit = "2E4A38"

    im = Image.new("RGB", (320, 240), (0, 0, 0))
    d = ImageDraw.Draw(im)
    for r in range(8):
        for c in range(12):
            box(d, -143 + 26 * c, -91 + 26 * r, 22, 22, 6,
                mix("0C2413", lit, want[r * 12 + c]))
    return im


# ---------------------------------------------------------------------------
# nixie - cztery lampy po siedem segmentow, base/faces/nixie.yaml
# ---------------------------------------------------------------------------
NX_X = (-104, -44, 44, 104)
# a b c d e f g, wzgledem srodka lampy: (dx, dy, w, h)
NX_SEG = ((0, -20, 26, 5), (10, -11, 5, 22), (10, 11, 5, 22), (0, 19, 26, 5),
          (-11, 11, 5, 22), (-11, -11, 5, 22), (0, -1, 26, 5))
NX_MAP = (0b1111110, 0b0110000, 0b1101101, 0b1111001, 0b0110011,
          0b1011011, 0b1011111, 0b1110000, 0b1111111, 0b1111011)
# Godzina w klipie. Na urzadzeniu tuby czytaja ha_time; tutaj zegara nie ma,
# wiec stoi jedna, ta sama co w poprzednim klipie, zeby bylo co porownac.
NX_TIME = (14, 37)


def _rnd(a, b):
    return (h32(a * 73 + b * 151) >> 16) & 0xFF


def nixie_frame(s, phase, f, pf=0):
    hh, mm = NX_TIME
    d4 = [hh // 10, hh % 10, mm // 10, mm % 10]
    glow = [255] * 4
    colon_on = True

    if phase == "listening":
        d4 = [_rnd(f, i) % 10 for i in range(4)]
    elif phase == "thinking":
        d4 = [_rnd(f // 2, i * 7) % 10 for i in range(4)]
        glow = [190] * 4
    elif phase == "replying":
        head = math.fmod(f * 55 / 100.0, 4.0)
        for i in range(4):
            dist = abs(i - head)
            if dist > 2.0:
                dist = 4.0 - dist
            crest = (1.0 - dist * 0.8) if dist < 1.25 else 0.0
            glow[i] = int(85 * 2.55 + 85 * 2.55 * crest)
            if dist < 0.6:
                d4[i] = _rnd(f, i * 3) % 10
    elif phase in ("timer", "error"):
        d4 = [0] * 4
        glow = [255 if f % 2 else 60] * 4
    elif phase == "muted":
        glow = [70] * 4
    else:
        breath = ((235 + int(20.0 * math.sin(f * 0.09))) // 8) * 8
        glow = [breath] * 4
        colon_on = (f % 10) < 5

    lit = "FF8A1E"
    if phase in ("timer", "error"):
        lit = "FF5A3C"
    elif phase == "muted":
        lit = "3A2A20"

    im = Image.new("RGB", (320, 240), rgb("0A0705"))
    d = ImageDraw.Draw(im)
    for i in range(4):
        base = min(glow[i], 255)
        over = min(max(glow[i] - 255, 0), 255)
        box(d, NX_X[i], 0, 52, 92, 24, rgb("1C1612"))
        # Poswiata w szkle za zapalona cyfra.
        box(d, NX_X[i], 0, 40, 80, 20, mix("1C1612", "3A1E0C", base))
        for sidx, (dx, dy, w, h) in enumerate(NX_SEG):
            on = (NX_MAP[d4[i]] >> (6 - sidx)) & 1
            colour = mix("2E1C10", lit, base) if on else rgb("2E1C10")
            if on and over:
                colour = tuple(colour[k] + (rgb("FFC87A")[k] - colour[k]) * over // 255
                               for k in range(3))
            box(d, NX_X[i] + dx, dy, w, h, 2, colour)
    for dy in (-16, 16):
        box(d, 0, dy, 10, 10, 5,
            mix("2E1C10", lit, min(glow[0], 255)) if colon_on else rgb("2E1C10"))
    return im


# ---------------------------------------------------------------------------
# scope - jedna krzywa na siatce, base/faces/scope.yaml
# ---------------------------------------------------------------------------
SC_X0, SC_X1 = 18.0, 302.0
SC_MID = (34 + 206) / 2.0
SC_AMP = (206 - 34) / 2.0 - 8.0
SC_N = 33
SC_ENV = [math.sin(3.14159 * k / (SC_N - 1)) ** 0.6 for k in range(SC_N)]
SC_THETA = [k / (SC_N - 1) * 6.2831853 for k in range(SC_N)]
SC_XPOS = [18 + (302 - 18) * k / (SC_N - 1) for k in range(SC_N)]
SC_LISS_Y = [SC_MID + SC_AMP * 0.8 * math.sin(2.0 * t) for t in SC_THETA]


def scope_frame(s, phase, f, pf=0):
    pts = []
    if phase == "thinking":
        for k in range(SC_N):
            t = SC_THETA[k]
            pts.append((160.0 + (SC_X1 - SC_X0) / 2.6 * math.sin(3.0 * t + f * 0.09),
                        SC_LISS_Y[k]))
    else:
        for k in range(SC_N):
            u, x = SC_THETA[k], SC_XPOS[k]
            if phase == "listening":
                swell = 0.38 + 0.62 * (0.5 + 0.5 * math.sin(f * 0.24))
                wave = (math.sin(u * 3.0 - f * 0.55)
                        + 0.38 * math.sin(u * 7.0 - f * 0.95)) / 1.38
                y = SC_MID - SC_AMP * 0.92 * swell * SC_ENV[k] * wave
            elif phase == "replying":
                y = SC_MID - SC_AMP * ((_rnd(f, k) / 255.0) - 0.5) * 1.7
            elif phase in ("timer", "error"):
                y = SC_MID - SC_AMP * (0.9 if ((k // 4 + f) % 2) else -0.9)
            elif phase == "muted":
                y = SC_MID
            else:
                y = SC_MID - SC_AMP * 0.06 * math.sin(u * 3.0 - f * 0.12)
            pts.append((x, y))

    im = Image.new("RGB", (320, 240), rgb("030C06"))
    d = ImageDraw.Draw(im)
    for x in (18, 65, 112, 160, 207, 254, 302):
        d.rectangle((x, 34, x, 34 + 171), fill=rgb("10331C"))
    for y in (34, 77, 120, 163, 206):
        d.rectangle((18, y, 18 + 283, y), fill=rgb("10331C"))
    d.rectangle((18, 34, 18 + 283, 34 + 171), outline=rgb("1E5A30"), width=2)
    d.text((20, 12), "CH1  20ms/div", font=font("Roboto Mono", 400, 12),
           fill=rgb("2E8A4A"))
    trace = "FF6A4A" if phase in ("timer", "error") else "5CFF8A"
    d.line([(int(x), int(y)) for x, y in pts], fill=rgb(trace), width=2, joint="curve")
    return im


# ---------------------------------------------------------------------------
# vu - dwie wskazowki za szklem, base/faces/vu.yaml
# ---------------------------------------------------------------------------
VU_PIVOT_X = (82, 238)
VU_PIVOT_Y, VU_LEN = 150, 60


def vu_ticks():
    """Kreski podzialki czytane z YAML-a, a nie przepisane recznie: jest ich
    tam 22, po 11 na miernik, i to jedyna wersja, ktora nie moze sie rozjechac.
    Bierzemy tylko lewy komplet - prawy jest jego kopia przesunieta o 156 px,
    wiec rysowanie obu daloby 11 kresek poza ekranem."""
    import io
    import re
    src = io.open(os.path.join(REPO, "base", "faces", "vu.yaml"),
                  encoding="utf-8").read()
    out = []
    for m in re.finditer(r"points:\n\s+- (\d+), (\d+)\n\s+- (\d+), (\d+)\n"
                         r"\s+line_width: 2\n\s+line_color: \$\{(\w+)\}", src):
        x0, y0, x1, y1, col = m.groups()
        out.append((int(x0), int(y0), int(x1), int(y1),
                    "C43628" if col == "vu_red_color" else "2A2218"))
    return out[:11]


VU_TICKS = None


def vu_frame(s, phase, f, pf=0):
    global VU_TICKS
    if VU_TICKS is None:
        VU_TICKS = vu_ticks()

    im = Image.new("RGB", (320, 240), rgb("14100A"))
    d = ImageDraw.Draw(im)
    for x in (10, 166):
        d.rounded_rectangle((x, 42, x + 143, 42 + 153), radius=8, fill=rgb("221C14"))
    for x in (18, 174):
        d.rounded_rectangle((x, 50, x + 127, 50 + 121), radius=6, fill=rgb("E8DCC0"))
    for x0, y0, x1, y1, col in VU_TICKS:
        d.line([(x0, y0), (x1, y1)], fill=rgb(col), width=2)
        d.line([(x0 + 156, y0), (x1 + 156, y1)], fill=rgb(col), width=2)
    ft = font("Roboto Mono", 500, 12)
    d.text((71, 118), "VU", font=ft, fill=rgb("2A2218"))
    d.text((227, 118), "VU", font=ft, fill=rgb("2A2218"))

    for si in range(2):
        if phase == "listening":
            deg = -50.0 + 78.0 * (0.5 + 0.5 * math.sin(f * 0.28 - si * 0.3))
        elif phase == "thinking":
            deg = -44.0 + 12.0 * math.sin(f * 0.8 + si)
        elif phase == "replying":
            deg = -50.0 + 100.0 * (_rnd(f, si * 5) / 255.0)
        elif phase in ("timer", "error"):
            deg = 45.0 if ((f + si) % 2) else -45.0
        elif phase == "muted":
            deg = -50.0
        else:
            deg = -48.0 + 3.0 * math.sin(f * 0.18 + si * 2.0)
        a = math.radians(deg)
        px, py = VU_PIVOT_X[si], VU_PIVOT_Y
        d.line([(px, py), (px + VU_LEN * math.sin(a), py - VU_LEN * math.cos(a))],
               fill=rgb("1A1410"), width=3)
    for x in (76, 232):
        d.ellipse((x, 144, x + 11, 144 + 11), fill=rgb("1A1410"))
    return im


DRAWN = {
    "aura": aura_frame,
    "bit": bit_frame,
    "crt": crt_frame,
    "iris": iris_frame,
    "kitt": kitt_frame,
    "nixie": nixie_frame,
    "pixel": pixel_frame,
    "rain": rain_frame,
    "scope": scope_frame,
    "vu": vu_frame,
}
