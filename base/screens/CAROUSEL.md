# Adding idle screens: the carousel

The idle screen is the middle of a small map. Two vertical neighbours hang off
home (settings drops in on a swipe down), and the **horizontal axis is a
carousel**: home plus any extra idle screens you install, stepped through with a
left or right swipe, wrapping at the ends.

```
                 page_settings          (swipe DOWN, belongs to home)
                       |
  ...  <-  home  -  weather  -  photos  ->  ...   (swipe LEFT / RIGHT, wraps)
                       |
                 (nothing here yet)       (swipe UP, belongs to home)
```

## Adding a screen

1. Copy [`carousel-example.yaml`](carousel-example.yaml) to a new file, e.g.
   `base/screens/weather.yaml`.
2. Rename its page `id` to something unique (`page_weather`).
3. Put your widgets in. Keep the full-screen `gesture_bubble` button last.
4. Add the file to your thin config's `files:` list, **after**
   `base/screens/home.yaml`.

That is all. There is no substitution to set - a screen joins the carousel by
being a `skip: false` page, and its order in the `files:` list is its order on
the ring. Home is always first.

```yaml
packages:
  core:
    files:
      - base/core.yaml
      - base/screens/home.yaml
      - base/screens/weather.yaml     # second stop
      - base/screens/photos.yaml      # third stop
      - base/faces/${assistant}.yaml
```

## Why it works this way

The core cannot name a page that lives in your package - it is compiled in a
separate file it never sees. So instead of a list of page names, the carousel
leans on LVGL's own page ring: `lvgl.page.next` / `previous` walk every page in
declaration order and step over any flagged `skip: true`. Everything that is not
a carousel stop - the status page, the boot and error screens, the phase pages,
settings, the character face - is `skip: true`, so a swipe only ever lands on a
real screen. After a conversation the core restores your place by **index**
(`show_page`), read back from the component after each swipe.

Two rules fall out of that:

- **A carousel screen is `skip: false`.** That is the only thing that makes it a
  stop. Forget it and the screen exists but no swipe reaches it.
- **The character face and settings are not carousel stops.** The face is home's
  tap-toggle (tap the clock to see the character, tap again to go back); settings
  is a vertical neighbour of home. Both are `skip: true`.

## Gestures

A page only receives a swipe if the object under your finger lets it through. The
example page covers itself with a transparent, full-screen `button` that has
`gesture_bubble: true`; the `on_swipe_left` / `on_swipe_right` triggers sit on
the page and call the core's `idle_swipe_left` / `idle_swipe_right` scripts. Copy
that shape and swiping works; drop the button or the flag and it will not.

Swipe sensitivity (`swipe_min_px`, `swipe_min_velocity`) and the slide animation
(`swipe_anim_*`) are core substitutions - see the top of `base/core.yaml`.
