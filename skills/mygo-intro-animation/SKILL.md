---
name: mygo-intro-animation
description: Build a first-run / install intro animation ("安装动画", "开场动画", "首次启动动画", onboarding intro) for a myGo native-UI macOS app - the product name hand-written over a full-screen transparent window with a breathing aurora, letters morphing into the logo, then the logo flying into the main window as it fades in. Use when the user wants an intro / launch / install animation for a myGo (github.com/egoist/mygo) app, or to port popMind's or Windeck's intro to another product.
---

# myGo intro animation

A reusable recipe, proven in popMind (`internal/views/onboarding*.go`) and Windeck
(`intro.go`, `intro_glyphs.go`). The flow, about 5 s:

1. A full-screen transparent window; a breathing aurora (shader) fades in behind the middle.
2. The product name is written by hand, stroke by stroke (`Path.Trim`), large and bold, drawing slowly nearer.
3. Some letters become the logo (the product-specific part); the other letters fade and drop.
4. The logo settles with a small bump while the aurora swells; the name and a tagline rise under it.
5. The main window opens transparent behind the intro while nothing moves, then fades in as the logo
   flies onto the logo's spot in it; at landing its own logo shows and the intro closes.

Everything is drawn with myGo's painter and one shader, computed from the time since the first
frame, so it is smooth and skippable.

## Before writing code

Collect, from the project and the user:

- The product name as shown (case matters: popMind's capital M), and the logo (`resources/icon.png`).
- The window the intro hands over to (launcher, switcher, onboarding window): its size, how it is
  positioned when shown, and where the logo sits in it (exact center, from its paddings).
- Whether the project has a native bridge that can fade a window (popMind: `native.AnimateWindowIn`);
  otherwise use `Window.SetOpacity` (see Hand-over).
- The project rules (AGENTS.md / CLAUDE.md): UI language, i18n, logging, GUI-testing workflow.

Then design the **name → logo story** and show it to the user before building. Look at the logo and
find letters it is made of, or shapes the letters can become:

- popMind: the logo is a speech bubble shaped like a "p" with a script "m" inside. The word's "p"
  opens into the bubble (point morph), the "M" moves into the bubble and reshapes into the "m"
  (part-matched morph), the other letters fade.
- Windeck: each letter turns into a window card, the cards stack into the deck of the logo, a square
  opens behind them.

Prefer a story where the strokes visibly carry over. Avoid erasing and redrawing: users asked for
the letter to *move into place and change*, not disappear.

## Building it

Start from `references/popmind_onboarding.go.txt` and `references/popmind_glyphs.go.txt` (copy, rename
the package and identifiers, adapt); `references/popmind_render_test.go.txt` renders frames and
`references/fade_window.go.txt` fades a window without native code. The live sources, when present:
`~/code/personal/popMind/internal/views/onboarding*.go` (+ `launcher.go`: `ShowTransparent`, `FadeIn`,
`introLogo`; `main.go`: the dev menu item) and `~/code/personal/Windeck/intro*.go` (cards variant,
hand-over to an onboarding window or the switcher). Pieces:

### 1. The logo as strokes

Trace the logo as monoline strokes in a 100×100 box (`pen`: `penAt`, `line`, `curve`, `arc`), stroke
width about 9-10. Render it beside the real icon (see Verification) and iterate until the shapes
match. Model each logo part as **one continuous stroke** where it can be (retrace a leg instead of
lifting the pen), so it can be morphed into.

### 2. The lettering

Hand-design the word as monoline strokes (`wordGlyphs`): baseline 0, x-height -40, caps -62,
descender +24; round bowls (rx 15, ry 20 for o/p/d), a forward slant (`x -= y*0.12`), stroke about
6.2 units (bold) at scale ~2.2. A custom monoline hand reads better than tracing a font's outline and
matches a script logo. Letters are drawn with `Path.Trim(0, drawn)`, staggered (gap 170-180 ms,
duration 560-620 ms); an i's dot pops with `easeOutBack`.

### 3. Morphs

- **Similar shapes** (p → bubble): sample both strokes to the same number of points by length
  (`subpath.sample(n)`), place each in window coordinates, `morph(a, b, t)` and stroke the polyline,
  stroke width easing from the word's to the logo's.
- **Different shapes** (M → script m): `matchStrokes(a, b, parts, n)` pairs ranges of segments part by
  part (up-stroke with lead-in, peak with shoulder, leg with leg...). Give parts of the target that the
  source lacks an empty source range (`{6,6}`): they **grow out of a point**, as if written on.
  Never let one long source part map onto a long winding target (it folds and crosses).
- Move first, reshape second: carry the source letter as it is into an inner box of the logo
  (`fitTo(..., box{...})`, clear of outer rings so strokes do not merge into a blob), then reshape.
- Check the morph by rendering its steps (0, .25, .5, .75, 1) side by side, large.

### 4. The aurora

Full-screen window: `Panel, Frameless, Transparent, DisableShadow, AlwaysOnTop, DisableResize`, the
size of the display's bounds. The `aurora` shader in the reference draws a soft veil behind the
lettering (light in light mode, dark in dark mode, so text reads on any wallpaper) and five drifting
colored lights, masked to fade out toward the screen edges, breathing over ~3.4 s; it swells once as
the logo settles and fades during the flight. Draw it only when `p.Accelerated()` (the CPU renderer is
too slow full screen); render tests force it.

### 5. Hand-over to the main window (no flash)

Do **not** draw a fake copy of the main window: its color never matches the real vibrancy and it
flashes. Instead:

1. ~350 ms before the logo flies (everything at rest), show the real window **transparent**:
   prepare alpha 0, then `Show()`. Showing a window blocks the main thread 50-100 ms; at rest it is
   invisible, mid-flight it is a hitch.
2. When the flight starts, fade the window to 1 over the flight (popMind: native
   `NSWindow.animator.alphaValue`, `AnimateWindowIn(h, 750, 0)`; without a bridge, step
   `Window.SetOpacity` from a goroutine every ~16 ms with an ease).
3. Hide the window's own logo (`Opacity(0)` behind a flag) until the flying logo lands, then show it
   and close the intro ~140 ms later.
4. Compute the landing spot from the intro window's **real** `Bounds()` read right after `Show()`:
   macOS pushes a full-screen window below the menu bar (Y = 33 on a notched MacBook), so the
   display's bounds are wrong by that much. Log both windows' bounds once to check.
5. The logo's exact center in the main window comes from its paddings. myGo's 4-value `Padding` is
   (top, right, bottom, left) as in CSS; e.g. footer left 8 + button 6 + half of 18 = 23.

### 6. When it plays

- Once per version: `onboarding.json` (or the app's equivalent) keeps the version it last played for;
  play when it differs from `mygo.App.Version()`, i.e. after each install or update. Decide before
  settings load if loading writes files.
- Development builds: never automatically; play with an env var (`POPMIND_ONBOARDING=1`) or a
  dev-only menu-bar item ("播放安装动画" / "Play the Intro"), left out of release builds.
- A click, Escape or Return skips it; skipping still hands over (show the window, fade it quickly).
- Play it even with Reduce Motion on: it is shown once and one click ends it. (Skipping under Reduce
  Motion made it never show on a Mac with that setting.)

### 7. Diagnostics

Log: shown (with bounds), first frame (delay, `gpu`), main window ready, fading in, done (reason,
total ms, frame count, longest frame gap and when it happened). Add fallback timers: finish if no frame
came within 2 s, and at total + 2.5 s. These logs answer "did it stutter / where".

## Verification

1. **Render tests** (CPU, `ui.Render`): call the paint function with fixed `ms` at key moments
   (writing, morph steps, logo, flight) in light and dark at 1440×900, and the logo strokes beside
   the icon; read the PNGs and iterate. A separate render of the morph steps catches folded strokes.
2. **Real run**: start the dev app with the env var and read the logs: first frame under ~300 ms,
   ~120 fps on ProMotion, longest gap only at the hand-over moment.
   Do **not** call `Window.CapturePage()` during playback (full-screen capture stalls it seconds).
   Never screenshot the user's screen to check; use the app's own captures or logs.
3. **Ask the user to watch it** (GUI): give exact steps (dev menu item), tell them what to look at
   (morph smoothness, landing alignment, any flash), and read the logs while they do.

## Pitfalls seen

- The user's Mac had Reduce Motion on; an intro that skips under it never showed.
- Point-morphing a two-peaked M straight into a three-arched m crossed strokes; part matching with
  grown parts fixed it.
- An M fitted to the full m box overlapped the bubble's ring and looked like a blob.
- A fake panel under the flying logo flashed against the real translucent window.
- Showing the main window mid-flight caused a 60-110 ms hitch; showing it transparent earlier moved
  the hitch to a moment where nothing moves.
- The landing was off by 4 pt (padding order) and 33 pt (window pushed below the menu bar).
- `CapturePage` during playback stretched a 5 s intro to 7 s.
