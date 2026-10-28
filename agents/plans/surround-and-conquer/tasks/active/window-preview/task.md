# Window preview

**Status:** ready

## Goal

The window paints the subject, the weed area, and the library's
arrows. Swap and the four color controls only change that paint.

## Do

- Edit `extensions/inkscape/weedlines_dialog.py` only.
- Paint the library regions and the paths from `build_arrow_paths`.
  Do not invent a second set of arrows. Do not reimplement
  topology.
- Weed lines use the weed-line color, on top of the checkerboard.
  After cuts exist, the checkerboard also covers the work region
  that mode already cuts. Do not change how the solver computes
  that region.
- Swap and the four plugin settings are the controls in
  `agents/architecture/preview.md`. They sit in the form above the
  preview. After either change, ask the library again and repaint.
  Do not store the colors in a preferences file.
- Leave the Start gate as the window-gate task left it. Do not add
  Surround and Conquer. Do not add the return line.
- Tests go in `tests/test_window_preview.py`. Offscreen when Qt
  loads. Skip when Qt cannot load. No Inkscape.

## Checks

- A solid subject paints in its fill. A subject with no paint, or
  with other paint, uses the default subject color. Weed area uses
  the two checkerboard colors. The view background outside that
  area is unchanged.
- Weed lines use the weed-line color, not the old orange pen.
- Preview arrows are the paths `build_arrow_paths` returns, in the
  three arrow colors.
- One swap control exchanges the regions, and the next press
  restores them. The four color controls change paint only. Their
  initial colors are the Paint table in the preview part.
- Start stays disabled when the check reports a defect.
- `pytest tests/test_window_preview.py` passes offscreen, or skips
  only because Qt is missing.

## Note

The developer writes what changed, why, and how it was checked.
The reviewer then writes the summary, the context worth keeping,
and the result.
