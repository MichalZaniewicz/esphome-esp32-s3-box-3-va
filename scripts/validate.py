#!/usr/bin/env python3
"""Offline sanity check for the ESPHome config.

ESPHome itself is the real validator, but a round trip through the dashboard is
slow and a YAML typo does not deserve one. This catches, locally:

  * YAML syntax errors (ESPHome's custom tags are stubbed out)
  * `${foo}` / `$foo` references with no matching substitution
  * substitutions that are defined but never used (dead config)
  * duplicate component `id:` values

    pip install pyyaml
    python validate.py ../base/core.yaml

Files that only make sense together - a core plus the screen packages that ride
on its substitutions - are checked as one config with --merge:

    python validate.py --merge ../base/core.yaml ../base/screens/home.yaml

Exit code is 1 if anything failed, so it works in a pre-commit hook.
"""
import re
import sys
from pathlib import Path

import yaml

# ESPHome tags carry no meaning for us; keep the value, drop the tag.
for tag in ("!secret", "!lambda", "!include", "!extend", "!remove", "!force"):
    yaml.SafeLoader.add_constructor(
        tag, lambda loader, node, t=tag: f"<{t[1:]}>"
    )
yaml.SafeLoader.add_multi_constructor(
    "!", lambda loader, suffix, node: f"<{suffix}>"
)

# Substitutions ESPHome injects itself, so an unresolved reference is expected.
BUILTIN_SUBS = {"name", "friendly_name", "device_name", "esphome_version"}

SUB_REF = re.compile(r"\$\{(\w+)\}|\$(\w+)")


# A YAML document with the SAME top-level key twice keeps only the last one, in
# silence. That is how a whole `interval:` block - a watchdog, as it happens -
# disappeared from core.yaml on 2026-07-20: it was added above an existing
# `interval:` and simply ceased to exist at parse time. Nothing downstream can
# notice, because by then the duplicate is already gone.
class DuplicateKeyLoader(yaml.SafeLoader):
    pass


def _no_duplicates(loader, node, deep=False):
    seen, mapping = set(), {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in seen:
            raise yaml.YAMLError(
                f"klucz '{key}' wystepuje dwa razy na tym samym poziomie "
                f"(linia {key_node.start_mark.line + 1}) - YAML zachowa TYLKO "
                f"ostatni, wczesniejszy zniknie bez sladu"
            )
        seen.add(key)
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


DuplicateKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _no_duplicates
)
for _tag in ("!secret", "!lambda", "!include", "!extend", "!remove", "!force"):
    DuplicateKeyLoader.add_constructor(
        _tag, (lambda t: lambda loader, node: f"<{t[1:]}>")(_tag)
    )


# Control-flow actions take a FIXED set of keys. An extra one means a line was
# indented one level too far and became a sibling of `condition:`/`then:`
# instead of a field inside the action underneath. That is still valid YAML, so
# nothing else here notices - the mis-indented line is simply dropped, and the
# widget silently never gets its text. This has bitten the repo twice.
CONTROL_KEYS = {
    "if": {"condition", "then", "else"},
    "while": {"condition", "then"},
    "wait_until": {"condition", "timeout"},
    "repeat": {"count", "then"},
}


def check_action_shape(node, path="root", problems=None):
    if problems is None:
        problems = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key in CONTROL_KEYS and isinstance(value, dict):
                # Only when the canonical key is present. ESPHome also accepts a
                # shorthand where the condition is written directly - `wait_until:
                # {lambda: ...}` - and in that form any key is fair game.
                canon = "count" if key == "repeat" else "condition"
                extra = set(value) - CONTROL_KEYS[key] if canon in value else set()
                if extra:
                    problems.append(
                        f"{path}.{key}: obce klucze {sorted(extra)} - "
                        f"dozwolone tylko {sorted(CONTROL_KEYS[key])}. "
                        f"Prawie na pewno zle wciecie."
                    )
            check_action_shape(value, f"{path}.{key}", problems)
    elif isinstance(node, list):
        for i, item in enumerate(node):
            check_action_shape(item, f"{path}[{i}]", problems)
    return problems


def check_wait_timeouts(node, path="root", problems=None):
    """Every `wait_until` must carry a `timeout`.

    This is the single most expensive mistake this project has made. A
    `wait_until` whose condition never becomes true does not fail and does not
    warn - it simply stops that automation forever, along with everything after
    it. On 2026-07-20 one of them hung on a speaker that never reported having
    stopped, so the line clearing `tts_reply_active` was never reached, and the
    device stayed deaf until it was rebooted. Nothing in the log said why.

    A timeout does not fix the underlying stall, but it turns "silently dead
    until power cycled" into "late", which is recoverable and visible.

    Only the canonical form is checked. `wait_until: {lambda: ...}` is the
    shorthand where the mapping IS the condition, and a timeout cannot be
    expressed there - those are reported separately so they get a second look
    rather than being silently accepted.
    """
    if problems is None:
        problems = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "wait_until" and isinstance(value, dict):
                if "condition" in value:
                    if "timeout" not in value:
                        problems.append(
                            f"{path}.wait_until: brak `timeout`. Warunek, ktory "
                            f"nigdy nie bedzie prawdziwy, zatrzymuje ta "
                            f"automatyzacje NA ZAWSZE i nic tego nie zglosi."
                        )
                else:
                    problems.append(
                        f"{path}.wait_until: skrocona forma bez `condition`, "
                        f"wiec nie da sie tu dac `timeout`. Rozpisz na "
                        f"`condition:` + `timeout:`."
                    )
            check_wait_timeouts(value, f"{path}.{key}", problems)
    elif isinstance(node, list):
        for i, item in enumerate(node):
            check_wait_timeouts(item, f"{path}[{i}]", problems)
    return problems


def collect_ids(node, out, path="root", in_action=False):
    """Collect id: DECLARATIONS only.

    Every ESPHome action is a dotted key (`script.execute`, `light.turn_on`,
    `mixer_speaker.apply_ducking`, ...) and an `id:` underneath one is a
    reference to a component declared elsewhere, not a second declaration.
    Component declarations never sit under a dotted key.
    """
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "id" and isinstance(value, str) and not value.startswith("<"):
                if not in_action:
                    out.setdefault(value, []).append(path)
            collect_ids(
                value,
                out,
                f"{path}.{key}",
                in_action or ("." in str(key)),
            )
    elif isinstance(node, list):
        for i, item in enumerate(node):
            collect_ids(item, out, f"{path}[{i}]", in_action)


def main() -> int:
    args = [a for a in sys.argv[1:] if a != "--merge"]
    merge = "--merge" in sys.argv
    if not args:
        print(__doc__)
        return 2

    if merge:
        return _check_merged(args)

    return _check(args)


def _check_merged(args) -> int:
    """Check several files as the single config ESPHome will assemble.

    Note this cannot be done by concatenating the text: each file has its own
    `substitutions:` block, and a YAML document with a duplicate top-level key
    keeps only the last one - which would silently drop the core's entire
    substitution set. The blocks have to be merged structurally instead.
    """
    print(f"(--merge: {', '.join(args)} jako jeden config)")
    problems = 0
    subs, ids, bodies = {}, {}, []

    for arg in args:
        path = Path(arg)
        text = path.read_text(encoding="utf-8")
        try:
            doc = yaml.load(text, Loader=DuplicateKeyLoader)
        except yaml.YAMLError as exc:
            print(f"  FAIL  {path}: YAML nie parsuje sie:\n{exc}")
            return 1
        shape = check_action_shape(doc, str(path))
        shape += check_wait_timeouts(doc, str(path))
        if shape:
            for msg in shape:
                print(f"  FAIL  {msg}")
            problems += len(shape)
        if not isinstance(doc, dict):
            print(f"  FAIL  {path}: top level nie jest mapowaniem")
            return 1
        subs.update(doc.get("substitutions") or {})
        collect_ids(doc, ids, path.name)
        bodies.append(re.sub(r"^substitutions:.*?(?=^\S)", "", text, flags=re.S | re.M))

    print("  OK    kazdy plik parsuje sie")

    used = set()
    for body in bodies:
        used |= {m.group(1) or m.group(2) for m in SUB_REF.finditer(body)}

    undefined = sorted(used - set(subs) - BUILTIN_SUBS)
    if undefined:
        print(f"  FAIL  uzyte, nigdzie nie zdefiniowane: {', '.join(undefined)}")
        problems += 1
    else:
        print(f"  OK    kazde ${{...}} ma substitution ({len(subs)} zdefiniowanych)")

    dupes = {k: v for k, v in ids.items() if len(v) > 1}
    if dupes:
        for dupe, where in dupes.items():
            print(f"  FAIL  duplikat id '{dupe}': {'; '.join(where)}")
        problems += 1
    else:
        print(f"  OK    {len(ids)} unikalnych id, bez kolizji")

    print("\n" + ("FAILED" if problems else "ALL GOOD"))
    return 1 if problems else 0


def _check(args) -> int:
    problems = 0
    for arg in args:
        path = Path(arg)
        text = path.read_text(encoding="utf-8")
        print(f"\n=== {path} ===")

        # 1. Does it parse?
        try:
            doc = yaml.load(text, Loader=DuplicateKeyLoader)
        except yaml.YAMLError as exc:
            print(f"  FAIL  YAML does not parse:\n{exc}")
            problems += 1
            continue
        print("  OK    YAML parses")

        if not isinstance(doc, dict):
            print("  FAIL  top level is not a mapping")
            problems += 1
            continue

        shape = check_action_shape(doc, str(path))
        shape += check_wait_timeouts(doc, str(path))
        if shape:
            for msg in shape:
                print(f"  FAIL  {msg}")
            problems += len(shape)
        else:
            print("  OK    ksztalt akcji i timeouty przy wait_until")

        subs = doc.get("substitutions") or {}

        # 2. References vs definitions. Strip the substitutions block itself so
        #    a default that quotes another key does not count as a use.
        body = re.sub(
            r"^substitutions:.*?(?=^\S)", "", text, flags=re.S | re.M
        )
        used = {m.group(1) or m.group(2) for m in SUB_REF.finditer(body)}

        undefined = sorted(used - set(subs) - BUILTIN_SUBS)
        if undefined:
            print(f"  FAIL  used but never defined: {', '.join(undefined)}")
            problems += 1
        else:
            print("  OK    every ${...} has a substitution")

        # A thin config exists precisely to define substitutions for a remote
        # package, so "unused here" says nothing. Only flag it on a standalone.
        if "packages" in doc:
            print("  SKIP  unused substitutions (this file feeds a package)")
        else:
            unused = sorted(set(subs) - used - BUILTIN_SUBS)
            if unused:
                print(f"  WARN  defined but never used: {', '.join(unused)}")

        # 3. Duplicate ids
        ids = {}
        collect_ids(doc, ids)
        dupes = {k: v for k, v in ids.items() if len(v) > 1}
        if dupes:
            for dupe, where in dupes.items():
                print(f"  FAIL  duplicate id '{dupe}': {'; '.join(where)}")
            problems += 1
        else:
            print(f"  OK    {len(ids)} unique ids, no collisions")

    print("\n" + ("FAILED" if problems else "ALL GOOD"))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
