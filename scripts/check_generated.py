"""Sprawdza, czy generatory nadal produkuja to, co lezy w repo.

Siedem plikow postaci nie jest pisanych recznie - powstaja ze skryptow w
scripts/gen/. Taki uklad ma jedna cicha pulapke i wpadlismy w nia 2026-07-20:
zoptymalizowalem kitt.yaml bezposrednio, generatora nie tknalem, i przez tydzien
nikt tego nie zauwazyl. Uruchomienie generatora skasowaloby te prace bez slowa
ostrzezenia - wykrylem to przypadkiem, sprawdzajac cos innego.

Ten skrypt zamienia to w blad. Regeneruje wszystko do pamieci, porownuje z tym,
co jest na dysku, i NIE zostawia po sobie zmian: pliki sa przywracane niezaleznie
od wyniku.

Uzycie:  python scripts/check_generated.py
Kod wyjscia 1, jesli cokolwiek sie rozjechalo.
"""
import io
import os
import re
import runpy
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, ".."))
GEN = os.path.join(HERE, "gen")
FACES = os.path.join(REPO, "base", "faces")


def generated_files():
    """Pliki, ktore generatory zapisuja - czytane z nich samych, nie z listy.

    Lista wpisana na sztywno rozjechalaby sie z rzeczywistoscia dokladnie tak,
    jak rozjechal sie generator, ktory ten skrypt ma pilnowac.
    """
    names = set()
    for fn in sorted(os.listdir(GEN)):
        if not (fn.startswith("gen_") and fn.endswith(".py")):
            continue
        text = io.open(os.path.join(GEN, fn), encoding="utf-8").read()
        # Literal .yaml Z LINII, KTORA COS ZAPISUJE - czyli przypisanie do OUT
        # albo open(..., "w"). Oba ksztalty wystepuja: reszta generatorow ma
        # `OUT = os.path.join(...)`, gen_scope_vu.py sklada sciezke w wywolaniu
        # open i pisze dwa pliki, a wersja pilnujaca tylko jednego wzorca po
        # cichu pomijala oba.
        #
        # Sam literal nie wystarcza: gen_picker.py CZYTA base/screens/face.yaml
        # i pliki postaci, zeby zebrac ich liczby. Wersja bez tego filtra brala
        # face.yaml za plik generowany i wywracala sie, szukajac go w base/faces.
        for line in text.splitlines():
            if not (re.search(r"\bOUT\w*\s*=", line) or
                    re.search(r'open\(.*"w"', line)):
                continue
            for m in re.finditer(r'"([A-Za-z0-9_]+\.yaml)"', line):
                names.add(m.group(1))
    return sorted(names)


def main():
    targets = generated_files()
    if not targets:
        print("STOP: nie wykrylem zadnych plikow generowanych - sprawdz scripts/gen/")
        return 1

    before = {}
    for name in targets:
        path = os.path.join(FACES, name)
        before[name] = io.open(path, encoding="utf-8", newline="").read()

    for fn in sorted(os.listdir(GEN)):
        if fn.startswith("gen_") and fn.endswith(".py"):
            sys.argv = [os.path.join(GEN, fn)]
            try:
                runpy.run_path(os.path.join(GEN, fn), run_name="__main__")
            except SystemExit:
                pass

    drifted = []
    for name in targets:
        path = os.path.join(FACES, name)
        after = io.open(path, encoding="utf-8", newline="").read()
        # Porownanie po normalizacji koncow linii. Generatory pisza "\n", a na
        # Windows z core.autocrlf=true kopia robocza ma "\r\n", wiec porownanie
        # bajt w bajt zglaszalo rozjazd wszystkich siedmiu plikow zawsze i u
        # kazdego - czyli mowilo "FAIL" tam, gdzie nie bylo zadnej roznicy.
        if after.replace("\r\n", "\n") != before[name].replace("\r\n", "\n"):
            drifted.append(name)
        # Przywracamy ZAWSZE, takze gdy sie zgadza - ten skrypt niczego nie zmienia.
        io.open(path, "w", encoding="utf-8", newline="").write(before[name])

    if drifted:
        print(f"FAIL  generator i repo rozjechaly sie: {', '.join(drifted)}")
        print("      Plik zostal poprawiony recznie, a generator nie - albo odwrotnie.")
        print("      Uruchomienie generatora skasowaloby te roznice bez ostrzezenia.")
        print("      Przenies poprawke do scripts/gen/ i wygeneruj ponownie.")
        return 1

    print(f"OK    {len(targets)} plikow generowanych zgadza sie z generatorami")
    return 0


sys.exit(main())
