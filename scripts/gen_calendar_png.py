"""Rysuje zrzut base/assets/calendar.png.

Off-device podglad base/screens/calendar.yaml, w natywnym 320x240 i fontami
urzadzenia - jak gen_notify_shopping.py, z tym samym zastrzezeniem: to nie jest
emulator LVGL, metryki tekstu roznia sie o piksel. Kolory czyta z pakietu;
wspolrzedne i wysokosci wierszy sa przepisane z gen_calendar.py.

Dane sa przykladowe, po angielsku - zrzut idzie do publicznego README, wiec
zadnych prawdziwych wydarzen z domowego kalendarza.

Wymaga Pillow i fontow w .esphome/font (zbuduj cokolwiek raz).

Uzycie:
    python scripts/gen_calendar_png.py
"""
import os

from PIL import Image, ImageDraw

from gen_calendar import HEAD_H, ROW_H, TEXT_X
from gen_climate import CORE, REPO, font_cache, gfont, icon_font, rgb, subs
from gen_notify_shopping import resolve

CALENDAR = os.path.join(REPO, "base", "screens", "calendar.yaml")
ASSETS = os.path.join(REPO, "base", "assets")
W, H = 320, 240
DOT, CAL, CHEVRON = "\U000F09DE", "\U000F0E18", "\U000F0140"

# (kind, time, text, live): 0 naglowek dnia, 1 wydarzenie z godzina, 2 caly dzien
ROWS = [
    (0, "Today", "Tuesday 17 November", False),
    (1, "14:30", "Bake bread for the weekend", True),
    (1, "17:30", "Football practice", False),
    (0, "Tomorrow", "Wednesday 18 November", False),
    (2, "", "Recycling collection", False),
    (1, "15:35", "Dentist, Anna", False),
    (1, "19:00", "Book club", False),
]


def main():
    cache = font_cache()
    s = resolve(subs(CALENDAR), subs(CORE))
    img = Image.new("RGB", (W, H), rgb(s["calendar_bg_color"]))
    d = ImageDraw.Draw(img)
    f_body, f_row, f_icon = gfont(cache, 16), gfont(cache, int(s["calendar_font_size"])), icon_font(cache, 18)
    accent, line, muted = rgb(s["calendar_accent_color"]), rgb(s["calendar_line_color"]), rgb(s["calendar_muted_color"])
    item, amber = rgb(s["calendar_item_color"]), rgb(s["calendar_allday_color"])
    n_events = sum(1 for r in ROWS if r[0] != 0) + 2   # i dwa ponizej krawedzi

    # Belka
    d.rectangle((0, 0, W, 33), fill=rgb(s["calendar_bar_color"]))
    d.line((0, 33, W, 33), fill=line)
    d.text((12, 17), CAL, font=f_icon, anchor="lm", fill=accent)
    d.text((40, 17), s["calendar_title"], font=f_body, anchor="lm", fill=rgb(s["calendar_title_color"]))
    count = str(n_events)
    tw = d.textlength(count, font=f_body)
    x1 = W - 10
    d.rounded_rectangle((x1 - tw - 16, 7, x1, 27), radius=10, fill=accent)
    d.text((x1 - 8 - tw / 2, 17), count, font=f_body, anchor="mm", fill=rgb(s["calendar_bg_color"]))

    # Wiersze; pad_top z generatora: 10 naglowek, 9 godzina, 7 tytul
    y = 34
    for kind, tm, text, live in ROWS:
        if y >= H:
            break
        if kind == 0:
            d.text((12, y + 10), tm, font=f_body, fill=accent)
            d.text((12 + d.textlength(tm + "  ", font=f_body), y + 10), text, font=f_body, fill=muted)
            y += HEAD_H
            continue
        if kind == 1:
            d.text((12, y + 9), tm, font=f_body, fill=accent if live else muted)
            x = TEXT_X
            d.text((x, y + 7), text, font=f_row, fill=item)
        else:
            d.text((12, y + 7 + 10), DOT, font=f_icon, anchor="lm", fill=amber)
            x = 12
            d.text((x + d.textlength(DOT, font=f_icon) + 8, y + 7), text, font=f_row, fill=item)
        d.line((x, y + ROW_H - 1, W - 12, y + ROW_H - 1), fill=line)
        y += ROW_H

    # "Jest wiecej nizej"
    cxm, cym = W // 2, H - 8 - 14
    d.ellipse((cxm - 14, cym - 14, cxm + 14, cym + 14), fill=rgb(s["calendar_bar_color"]), outline=line)
    d.text((cxm, cym + 1), CHEVRON, font=f_icon, anchor="mm", fill=accent)
    img.save(os.path.join(ASSETS, "calendar.png"))
    print("calendar.png ->", ASSETS)


if __name__ == "__main__":
    main()
