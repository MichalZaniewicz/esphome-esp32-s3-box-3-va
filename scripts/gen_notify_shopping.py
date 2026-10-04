"""Rysuje zrzuty base/assets/notify.png i base/assets/shopping.png.

Off-device podglad base/screens/notify.yaml i base/screens/shopping.yaml, w
natywnym 320x240 i fontami urzadzenia - jak gen_climate.py, z tym samym
zastrzezeniem: to nie jest emulator LVGL, metryki tekstu roznia sie o piksel.
Kolory czyta z pakietow; wspolrzedne sa przepisane z ich blokow `lvgl:`.

Wymaga Pillow i fontow w .esphome/font (zbuduj cokolwiek raz).

Uzycie:
    python scripts/gen_notify_shopping.py
"""
import os

from PIL import Image, ImageDraw

from gen_climate import CORE, REPO, font_cache, gfont, icon_font, rgb, subs

NOTIFY = os.path.join(REPO, "base", "screens", "notify.yaml")
SHOPPING = os.path.join(REPO, "base", "screens", "shopping.yaml")
ASSETS = os.path.join(REPO, "base", "assets")
W, H = 320, 240

WASHER, DOT, CART, CHEVRON = "\U000F072A", "\U000F09DF", "\U000F0110", "\U000F0140"


def resolve(s, core):
    """Rozwija ${accent_color} i podobne odwolania do rdzenia."""
    out = {}
    for k, v in s.items():
        if v.startswith("${") and v.endswith("}"):
            v = core.get(v[2:-1], v)
        out[k] = v
    return out


def wrap(d, text, font, width):
    lines, cur = [], ""
    for word in text.split():
        trial = (cur + " " + word).strip()
        if d.textlength(trial, font=font) <= width:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def notify(cache, core):
    s = resolve(subs(NOTIFY), core)
    img = Image.new("RGB", (W, H), rgb(s["notify_bg_color"]))
    d = ImageDraw.Draw(img)
    f_icon, f_title, f_msg = icon_font(cache, 56), gfont(cache, 26, 700), gfont(cache, 16)

    title = wrap(d, "Laundry is done", f_title, 290)
    msg = wrap(d, "The washer has finished. Time to hang it up before it creases.", f_msg, 290)
    ih, th, lh = 56, 32 * len(title), 20
    mh = lh * len(msg) + 8
    y = max(4, (H - 4 - (ih + 6 + th + mh)) // 2)   # ten sam wzor co notify_show

    d.text((W // 2, y), WASHER, font=f_icon, anchor="ma", fill=rgb(s["notify_icon_color"]))
    y += ih + 6
    for line in title:
        d.text((W // 2, y), line, font=f_title, anchor="ma", fill=rgb(s["notify_title_color"]))
        y += 32
    y += 8
    for line in msg:
        d.text((W // 2, y), line, font=f_msg, anchor="ma", fill=rgb(s["notify_message_color"]))
        y += lh

    d.rectangle((0, H - 4, W, H), fill=rgb(s["notify_track_color"]))
    d.rectangle((0, H - 4, int(W * 0.6), H), fill=rgb(s["notify_bar_color"]))
    img.save(os.path.join(ASSETS, "notify.png"))


def shopping(cache, core):
    s = resolve(subs(SHOPPING), core)
    img = Image.new("RGB", (W, H), rgb(s["shopping_bg_color"]))
    d = ImageDraw.Draw(img)
    f_body, f_row, f_icon = gfont(cache, 16), gfont(cache, 20), icon_font(cache, 20)
    accent, line = rgb(s["shopping_accent_color"]), rgb(s["shopping_line_color"])
    items = ["Milk", "Rye bread", "Eggs (a dozen)", "Butter", "Vine tomatoes",
             "Coffee beans", "Potatoes"]

    # Belka
    d.rectangle((0, 0, W, 33), fill=rgb(s["shopping_bar_color"]))
    d.line((0, 33, W, 33), fill=line)
    d.text((12, 17), CART, font=f_icon, anchor="lm", fill=accent)
    d.text((40, 17), s["shopping_title"], font=f_body, anchor="lm", fill=rgb(s["shopping_title_color"]))
    count = str(len(items))
    tw = d.textlength(count, font=f_body)
    x1 = W - 10
    d.rounded_rectangle((x1 - tw - 16, 7, x1, 27), radius=10, fill=accent)
    d.text((x1 - 8 - tw / 2, 17), count, font=f_body, anchor="mm", fill=rgb(s["shopping_bg_color"]))

    # Karta z wierszami (widac 5 z 7, reszta pod krawedzia)
    cx, cy, cw, ch = 8, 42, 304, 190
    card = Image.new("RGB", (cw, ch), rgb(s["shopping_card_color"]))
    cd = ImageDraw.Draw(card)
    for i, name in enumerate(items):
        top = i * 38
        if top >= ch:
            break
        cd.text((14, top + 8 + 11), DOT, font=f_icon, anchor="lm", fill=accent)
        cd.text((14 + 26, top + 8 + 11), name, font=f_row, anchor="lm", fill=rgb(s["shopping_item_color"]))
        cd.line((0, top + 37, cw, top + 37), fill=line)
    # Pasek przewijania: 5 z 7 widocznych, na gorze
    track = ch - 16
    cd.rounded_rectangle((cw - 6, 8, cw - 3, 8 + int(track * 5 / 7)), radius=2, fill=accent)
    mask = Image.new("L", (cw, ch), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, cw - 1, ch - 1), radius=12, fill=255)
    img.paste(card, (cx, cy), mask)
    d.rounded_rectangle((cx, cy, cx + cw - 1, cy + ch - 1), radius=12, outline=line)

    # "Jest wiecej nizej"
    cxm, cym = W // 2, H - 14 - 14
    d.ellipse((cxm - 14, cym - 14, cxm + 14, cym + 14), fill=rgb(s["shopping_bar_color"]), outline=line)
    d.text((cxm, cym + 1), CHEVRON, font=f_icon, anchor="mm", fill=accent)
    img.save(os.path.join(ASSETS, "shopping.png"))


def main():
    cache = font_cache()
    core = subs(CORE)
    notify(cache, core)
    shopping(cache, core)
    print("notify.png, shopping.png ->", ASSETS)


if __name__ == "__main__":
    main()
