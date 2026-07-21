"""Buduje i wgrywa OTA, ale odmawia, jesli w firmwarze siedzi SSID-atrapa.

Po co to istnieje: 2026-07-20 poszedl do Boxa build zrobiony z secrets.yaml, w
ktorym stalo jeszcze "TWOJE_SSID". Firmware zaczal szukac sieci o tej nazwie,
urzadzenie wypadlo z sieci i wrocilo dopiero przez awaryjny hotspot i portal
przechwytujacy - czyli wymagalo czlowieka fizycznie przy Boxie.

Pulapka jest nadal zywa i ma teraz druga twarz: repo/secrets.yaml trzyma
wifi_ssid: "test" na potrzeby configow sprawdzajacych schemat (_*.yaml). Config,
ktory !include-uje repo/base/core.yaml, rozwija !secret wzgledem TEGO pliku, a
nie wzgledem katalogu projektu - i po cichu bierze "test".

Czego NIE da sie juz uzyc do kontroli: `esphome config | grep networks`. Na
2026.7.1 dump drukuje `ssid: !secret 'wifi_ssid'` zamiast wartosci, wiec nie
odroznia prawdziwego SSID od atrapy. Sprawdzamy wygenerowany C++, bo to jest to,
co realnie idzie do kompilatora.

Uzycie:
    python scripts/flash.py ../alexa-kuchnia-local.yaml
    python scripts/flash.py ../alexa-kuchnia-local.yaml --dry-run   # bez wgrania

Kod wyjscia 1, jesli cokolwiek jest nie tak. Nie wgrywa "na wszelki wypadek".
"""
import argparse
import io
import os
import re
import subprocess
import sys

# Cokolwiek, co wyglada jak niewypelniony placeholder. Lista jest celowo szeroka:
# koszt falszywego alarmu to jedno pytanie, koszt przeoczenia to wieczor z USB.
PLACEHOLDERS = re.compile(
    r"^(TWOJE_|YOUR_|CHANGEME|CHANGE_ME|PLACEHOLDER|test$|testtest|XXX|FIXME|ssid$)",
    re.IGNORECASE,
)


def run(cmd, **kw):
    print(f"  $ {' '.join(cmd)}")
    return subprocess.run(cmd, **kw)


def device_name(config_path):
    """Nazwa urzadzenia = nazwa katalogu builda. Czytamy ja z rozwinietego configu."""
    out = subprocess.run(
        ["esphome", "config", config_path],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if out.returncode != 0:
        print("FAIL  `esphome config` nie przeszlo:")
        print(out.stderr[-2000:])
        return None
    m = re.search(r"^\s*name:\s*(\S+)\s*$", out.stdout, re.MULTILINE)
    return m.group(1) if m else None


def compiled_ssid(build_dir):
    """SSID tak, jak wyladowal w wygenerowanym main.cpp - podstawa prawdy."""
    main_cpp = os.path.join(build_dir, "src", "main.cpp")
    if not os.path.isfile(main_cpp):
        return None, f"nie ma {main_cpp} - kompilacja nie doszla do generowania zrodel"
    text = io.open(main_cpp, encoding="utf-8", errors="replace").read()
    hits = re.findall(r'set_ssid\("([^"]*)"\)', text)
    if not hits:
        return None, "w main.cpp nie ma ani jednego set_ssid(...) - sprawdz blok wifi"
    unique = sorted(set(hits))
    if len(unique) > 1:
        return None, f"main.cpp ma kilka roznych SSID: {unique} - to nie powinno sie zdarzyc"
    return unique[0], None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("config")
    ap.add_argument("--device", default="192.168.1.123", help="adres OTA")
    ap.add_argument("--dry-run", action="store_true", help="zbuduj i sprawdz, nie wgrywaj")
    args = ap.parse_args()

    config = os.path.abspath(args.config)
    if not os.path.isfile(config):
        print(f"FAIL  nie ma pliku {config}")
        return 1
    workdir = os.path.dirname(config)
    os.chdir(workdir)

    print("[1/4] Odczytuje nazwe urzadzenia")
    name = device_name(config)
    if not name:
        return 1
    build_dir = os.path.join(workdir, ".esphome", "build", name)
    print(f"      {name}")

    print("[2/4] Kompiluje")
    if run(["esphome", "compile", config]).returncode != 0:
        print("FAIL  kompilacja nie przeszla - nie wgrywam")
        return 1

    print("[3/4] Sprawdzam, co naprawde wyladowalo jako SSID")
    ssid, err = compiled_ssid(build_dir)
    if err:
        print(f"FAIL  {err}")
        return 1
    if PLACEHOLDERS.match(ssid):
        print(f"STOP  skompilowany SSID to '{ssid}' - to wyglada na atrape.")
        print("      Wgranie tego zdejmie Boxa z sieci i bedzie wymagac fizycznego")
        print("      dostepu (hotspot awaryjny + portal). NIE WGRYWAM.")
        print("      Sprawdz, czy config nie ciagnie !secret z repo/secrets.yaml.")
        return 1
    print(f"      OK: '{ssid}'")

    if args.dry_run:
        print("[4/4] --dry-run: zatrzymuje sie przed wgraniem")
        return 0

    print(f"[4/4] Wgrywam OTA na {args.device}")
    if run(["esphome", "upload", config, "--device", args.device]).returncode != 0:
        print("FAIL  upload nie przeszedl.")
        print("      Sprawdz, czy urzadzenie odpowiada, ZANIM sprobujesz ponownie.")
        return 1

    print("")
    print("Wgrane. Potwierdz teraz, ze Box odpowiada na API, zanim zrobisz cokolwiek")
    print("dalej - jesli nie odpowiada, zatrzymaj sie i zglos, nie powtarzaj wgrania.")
    return 0


sys.exit(main())
