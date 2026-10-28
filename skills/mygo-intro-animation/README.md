# mygo-intro-animation

Portable agent skill: build a first-run / install intro animation for a macOS app made with
[myGo](https://github.com/egoist/mygo) native UI. Works in **Claude Code** and **OpenAI Codex CLI** from one source tree.

The intro, about 5 seconds, over a full-screen transparent window:

1. A breathing aurora (one myGo shader) fades in behind the middle of the screen.
2. The product name is written by hand, stroke by stroke, large and bold.
3. Some letters become the logo (popMind: the "p" opens into its speech bubble and the "M" moves in
   and turns into the script "m"; Windeck: the letters become window cards that stack into its deck).
4. The logo settles, the name rises under it.
5. The main window opens transparent behind it and fades in as the logo flies onto its spot; no fake
   window, no flash, no hitch.

It plays once per version (after each install or update), can be replayed from a development-only
menu item, and is skipped with a click or Escape.

## What the skill covers

- Designing the name → logo story per product (shown to the user before building)
- Tracing the logo as monoline strokes, hand-lettering the name
- Two morphs: point morph for similar strokes, part-matched morph (with parts that grow out of a
  point) for different ones
- The aurora shader, the hand-over to the main window, the once-per-version rule, diagnostics logs
- Verification: render tests of key frames and morph steps, a real run with frame stats, then the user
- The pitfalls met on the way (Reduce Motion, folded morphs, landing offsets, show-window hitches)

## Layout

```
skills/mygo-intro-animation/
├── SKILL.md                              # agent contract
├── README.md                             # this file
├── references/
│   ├── popmind_onboarding.go.txt         # popMind's intro: timeline, aurora shader, hand-over, logs
│   ├── popmind_glyphs.go.txt             # lettering and logo strokes, sampling, morph matching
│   ├── popmind_render_test.go.txt        # renders frames to PNGs to review
│   └── fade_window.go.txt                # fade a window in without native code
└── scripts/
    └── install.sh
```

## Install

```bash
./skills/mygo-intro-animation/scripts/install.sh
```

Then ask for it: "给这个产品做个安装动画", "add a first-run intro animation".
