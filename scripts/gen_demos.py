"""Rysuje demo postaci: klipy do base/assets/demo/ i siatke base/assets/characters.png.

Off-device podglad base/screens/face.yaml. Czyta te same substitutions co
firmware - najpierw domyslne silnika, potem plik postaci - i odgrywa skrypt
ticka faza po fazie, wiec zmiana liczby w base/faces/*.yaml widac w klipie bez
kompilacji i bez wgrywania. Wiernosc byla sprawdzana na `rufus`: klatka w klatke
zgadza sie z klipem w repo.

NIE lezy w scripts/gen/ celowo. Tamte pliki uruchamia check_generated.py przy
kazdym sprawdzeniu, a to sa binaria wazace megabajty - regenerowane co chwile
zasmiecalyby diff bez powodu. Klipy zmieniaja sie tylko wtedy, gdy ktos ruszy
postac, i wtedy uruchamia sie to recznie.

Wymaga Pillow:  pip install pillow

Uzycie:
    python scripts/gen_demos.py                # wszystkie klipy + siatka
    python scripts/gen_demos.py spike hacker   # tylko wskazane klipy
    python scripts/gen_demos.py --grid         # tylko characters.png
"""
import io
import os
import re
import sys

from PIL import Image, ImageDraw, ImageFont

from gen_demos_drawn import DRAWN

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, ".."))
FACES = os.path.join(REPO, "base", "faces")
ASSETS = os.path.join(REPO, "base", "assets")
ENGINE = os.path.join(REPO, "base", "screens", "face.yaml")

# Klip: faza i ile tickow ja trzymamy. 39 klatek po 120 ms, jak reszta demek.
CLIP = [("idle", 8), ("listening", 8), ("thinking", 8), ("replying", 15)]
# Siatka: kolumna na faze, wiersz na postac. Numer klatki dobrany tak, zeby
# kazda kolumna pokazywala faze w charakterystycznym momencie.
GRID = [("idle", 1), ("listening", 21), ("thinking", 31), ("replying", 41),
        ("timer", 51)]
SCALE = 0.85          # 272x204, rozmiar klipow w repo
TICK_MS = 120
# Podpis fazy: goly tekst z cienkim czarnym obrysem, NIE wypelniony prostokat.
# Belka jest niewidoczna na czarnym tle i dlatego przetrwala tak dlugo, ale na
# agnes, genie, wizardzie czy franky'm czytala sie jak pasek wyciety z obrazka.
# Obrys robi to samo - trzyma napis czytelny nad czymkolwiek - i nic nie zasłania.
LABEL_STROKE = 1
# Terminal ma swoj naglowek w lewym gornym rogu, a oscyloskop podpis kanalu -
# tam podpis fazy wchodzilby na nie. U reszty gora jest wolna.
LABEL_BOTTOM = {"crt", "scope"}

SUB = re.compile(r"^  ([a-z_0-9]+):\s*(.+?)\s*$")


def subs(path):
    """Blok substitutions z pakietu ESPHome."""
    out, inside = {}, False
    for line in io.open(path, encoding="utf-8"):
        if line.startswith("substitutions:"):
            inside = True
            continue
        if not inside:
            continue
        # Pusta linia i komentarz NIE koncza bloku. Wersja, ktora tego nie
        # wiedziala, urywala sie na komentarzu w kolumnie 0 - taki maja franky,
        # genie, momo i wizard - i po cichu rysowala te cztery postacie
        # geometria domyslna silnika, czyli pipa. Wyszlo dopiero z siatki.
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


def load(name):
    s = subs(ENGINE)
    s.update(subs(os.path.join(FACES, name + ".yaml")))
    # Pakiet jezykowy idzie ostatni w files:, wiec wygrywa - i tylko `crt` ma
    # cokolwiek do przetlumaczenia. Bez tego klip terminala mowi co innego niz
    # urzadzenie, na ktorym en.yaml jest domyslny.
    s.update(subs(os.path.join(REPO, "base", "lang", "en.yaml")))
    return s


def artwork_characters():
    out = []
    for fn in sorted(os.listdir(FACES)):
        if not fn.endswith(".yaml") or fn == "picker.yaml":
            continue
        if "face_background_file" in subs(os.path.join(FACES, fn)):
            out.append(fn[:-5])
    return out


try:
    FONT = ImageFont.truetype("arial.ttf", 11)
except OSError:
    FONT = ImageFont.load_default()


class Face:
    """Silnik z base/screens/face.yaml, przepisany 1:1 na PIL."""

    def __init__(self, name):
        self.s = load(name)
        self.i = lambda k: int(self.s[k])
        self.bg = Image.open(os.path.join(FACES, name + ".png")).convert("RGB")
        self.color = self.hexc(self.s["face_color"])
        self.mouth_color = self.hexc(self.s["face_mouth_color"])
        self.pupil_color = self.hexc(self.s["face_pupil_color"])
        self.alarm = self.hexc(self.s["face_alarm_color"])

    @staticmethod
    def hexc(v):
        v = int(v, 16)
        return (v >> 16 & 255, v >> 8 & 255, v & 255)

    def draw(self, eye_w, eye_h, eye_dx, pupil, gx, mouth_w, mouth_h, alarm):
        i = self.i
        im = self.bg.copy()
        d = ImageDraw.Draw(im)
        cx, cy = 160 + i("face_center_x"), 120
        eye_col = self.alarm if alarm else self.color
        mouth_col = self.alarm if alarm else self.mouth_color

        def box(x, y, w, h, r, col):
            r = max(0, min(r, w // 2, h // 2))
            d.rounded_rectangle((x - w / 2, y - h / 2,
                                 x - w / 2 + w - 1, y - h / 2 + h - 1),
                                radius=r, fill=col)

        ey = cy + i("face_eye_y")
        for sign in (-1, 1):
            box(cx + sign * i("face_eye_offset") + eye_dx, ey,
                eye_w, eye_h, i("face_eye_radius"), eye_col)
        if pupil:
            pw, ph = pupil
            for sign in (-1, 1):
                box(cx + sign * i("face_eye_offset") + gx, ey,
                    pw, ph, i("face_pupil_radius"), self.pupil_color)
        box(cx, cy + i("face_mouth_y"), mouth_w, mouth_h,
            i("face_mouth_radius"), mouth_col)
        return im

    def frame(self, phase, f):
        """Jeden tick face_tick_script dla danej fazy."""
        i = self.i
        pw, ph = i("face_pupil_w"), i("face_pupil_h")
        gaze = i("face_gaze_dx")
        if phase == "idle":
            t = f % i("face_idle_cycle")
            if t in (0, 5):                              # face_blink
                return self.draw(i("face_eye_w"), i("face_eye_h_shut"), 0, None, 0,
                                 i("face_mouth_w"), i("face_mouth_h"), False)
            g = (gaze * 2) // 3
            gx = g if 30 <= t < 40 else (-g if 50 <= t < 60 else 0)
            return self.draw(i("face_eye_w"), i("face_eye_h"), 0, (pw, ph), gx,
                             i("face_mouth_w"), i("face_mouth_h"), False)
        if phase == "listening":
            p = i("face_listen_pulse")
            h = i("face_eye_h_wide") + [0, p // 2, p, p // 2][(f // 2) % 4]
            dl = i("face_pupil_dilate")
            return self.draw(i("face_eye_w"), h, 0, (pw + dl, ph + dl), 0,
                             i("face_mouth_o_w"), i("face_mouth_o_h"), False)
        if phase == "thinking":
            gx = gaze if (f // 3) % 2 else -gaze
            return self.draw(i("face_eye_w"), i("face_eye_h_think"), 0, (pw, ph), gx,
                             i("face_mouth_think_w"), i("face_mouth_h"), False)
        if phase == "replying":
            mh = i("face_mouth_open_h") if f % 2 else i("face_mouth_h")
            return self.draw(i("face_eye_w"), i("face_eye_h"), 0, (pw, ph), 0,
                             i("face_mouth_w"), mh, False)
        if phase == "timer":
            dx = i("face_shake_dx") if f % 2 else -i("face_shake_dx")
            sh = i("face_pupil_shrink")
            return self.draw(i("face_eye_w"), i("face_eye_h_wide"), dx,
                             (pw - sh, ph - sh), dx,
                             i("face_mouth_alarm_w"), i("face_mouth_alarm_h"), True)
        if phase == "muted":
            return self.draw(i("face_eye_w"), i("face_eye_h_shut"), 0, None, 0,
                             i("face_mouth_small_w"), i("face_mouth_h"), False)
        if phase == "error":
            sh = i("face_pupil_shrink")
            return self.draw(i("face_eye_w"), i("face_eye_h_narrow"), 0,
                             (pw - sh, ph - sh), 0,
                             i("face_mouth_error_w"), i("face_mouth_h"), True)
        raise ValueError(phase)


def clip(name):
    s = load(name)
    drawn = DRAWN.get(name)
    face = None if drawn else Face(name)
    # Kazda postac tyka wlasnym tempem - rysujace sie same chodza na 100 ms,
    # silnik twarzy na 120. Klip ma trwac tyle, ile trwa naprawde.
    tick = s.get(f"{name}_tick", "").rstrip("ms")
    tick = int(tick) if tick.isdigit() else TICK_MS

    frames, f, pf = [], 0, 0
    prev_phase = None
    for phase, n in CLIP:
        for _ in range(n):
            # pf to tiki od zmiany fazy - `crt` odlicza po nim wypisywanie
            # odpowiedzi, zeby zaczynala sie od pierwszej litery.
            pf = 0 if phase != prev_phase else pf + 1
            prev_phase = phase
            im = (drawn(s, phase, f, pf) if drawn else face.frame(phase, f))
            im = im.resize((int(320 * SCALE), int(240 * SCALE)), Image.LANCZOS)
            y = im.height - 18 if name in LABEL_BOTTOM else 4
            ImageDraw.Draw(im).text((6, y), phase, fill=(255, 255, 255), font=FONT,
                                    stroke_width=LABEL_STROKE, stroke_fill=(0, 0, 0))
            frames.append(im)
            f += 1
    out = os.path.join(ASSETS, "demo", f"demo-{name}.gif")
    frames[0].save(out, save_all=True, append_images=frames[1:],
                   duration=tick, loop=0, optimize=True)
    print(f"demo-{name}.gif: {len(frames)} klatek, {tick} ms")


def grid():
    names = artwork_characters()
    sheet = Image.new("RGB", (320 * len(GRID), 240 * len(names)))
    for row, name in enumerate(names):
        face = Face(name)
        for col, (phase, f) in enumerate(GRID):
            im = face.frame(phase, f)
            ImageDraw.Draw(im).text((6, 4), f"{name} - {phase}",
                                    fill=(255, 255, 255), font=FONT,
                                    stroke_width=LABEL_STROKE, stroke_fill=(0, 0, 0))
            sheet.paste(im, (col * 320, row * 240))
    sheet.save(os.path.join(ASSETS, "characters.png"))
    print(f"characters.png: {len(names)} postaci x {len(GRID)} faz")


def main(argv):
    if argv == ["--grid"]:
        grid()
        return
    for name in (argv or artwork_characters() + sorted(DRAWN)):
        clip(name)
    if not argv:
        grid()


if __name__ == "__main__":
    main(sys.argv[1:])
