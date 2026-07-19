# Languages

Every string the screens draw is a substitution, and a language is just a file
that sets them. English is the default, baked into the screens themselves, so a
config that lists no language package speaks English.

## Using one

Add the file to your package's `files:` list, **after** the screens:

```yaml
packages:
  core:
    url: https://github.com/MichalZaniewicz/esphome-esp32-s3-box-3-va
    files:
      - base/core.yaml
      - base/screens/home.yaml
      - base/lang/pl.yaml      # <- must come last
```

Order is not cosmetic. ESPHome turns each entry in `files:` into its own package
and resolves later-declared packages at a higher priority, letting them win
substitution conflicts. A language file listed *before* the screen it translates
is silently ignored - you get English and no error.

You can also skip the file entirely and set individual substitutions in your own
config, which always outranks every package. That is the right move for a one-off
tweak ("Kitchen" instead of "Inside"), not for a whole language.

## Adding one

1. `cp en.yaml xx.yaml` - `en.yaml` is the reference and always lists every key.
2. Translate the right-hand sides. Keep the keys exactly as they are.
3. Check your characters render. The fonts use the `GF_Latin_Core` glyphset,
   which covers Western *and* Central European Latin - Polish, Czech, Hungarian
   and Turkish accents are all in there. Anything outside it (Greek, Cyrillic,
   CJK) needs `font_glyphsets` extended in your own config, and the Google Fonts
   glyphsets are increments rather than supersets, so list both rather than
   swapping one for the other.
4. Pull requests welcome.

### Notes for translators

- `weekday_names` starts at **Sunday**, `month_names` at **January**. Both are
  C string-array initialisers: quoted, comma-separated, no trailing comma.
- The date reads `<weekday>, <day> <month>`, so languages that inflect months
  after a number want that form - Polish uses the genitive (`19 lipca`, not
  `19 lipiec`).
- `home_hint_text` sits under the clock in a small grey font. Roughly 40
  characters fit on a 320 px screen; longer text is clipped, not wrapped.
