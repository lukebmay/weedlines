# Window surround

**Status:** done

## Goal

The window opens on Surround and Conquer, paints the library
surrounds, and stops that mode on approval. Frame, grid, and
island-hop still cut.

## Do

- Edit `extensions/inkscape/weedlines_dialog.py`. The mode value
  is `Surround and Conquer`. Put that entry on the mode list
  with the other three. Missing or blank mode selects it, and so
  does that value in any case. `frame`, `grid`, and `island-hop`
  still select those entries. Any other value selects frame.
- Call `build_surrounds(subject, distance)` from `weedlib`. Do
  not reimplement the expansion. Stroke each returned path in
  the weed-line color, on top of the checkerboard. Do not fill
  those paths.
- The surround rules are Surround preview in
  `agents/architecture/preview.md` and Surround and Conquer in
  `agents/architecture/algorithms.md`. The figure check still
  gates this preview (`agents/architecture/preflight.md`). Paint
  no surround while a defect exists, and do not call
  `build_surrounds` then. Start stays disabled for every mode
  while a defect exists.
- The distance control's label is "Surround distance". Show it
  only in this mode. It starts at five percent of the smaller
  side of the design bounds, keeps a value the person sets while
  the window is open, and does not go below zero. Ask the
  library again when that distance changes, when the person
  swaps, or when the mode becomes Surround and Conquer. Padding,
  spacing, and collar do not change the surround.
- Start Algorithm approves the surrounds that are showing. It
  does not call `generate_weeds`, does not write a result, and
  does not enable Apply. The lines stay. The distance control
  is then disabled. A control labeled "Change surround", shown
  only in this mode, clears that approval, enables the distance,
  and the preview follows the distance again. Swap, and a change
  to another mode, also clear an approval. A weed-line color
  change repaints the lines and does not clear the approval.
- Frame, grid, and island-hop still pass the subject to
  `generate_weeds` and still cut. Do not add conquer cuts, a
  second surround, or a smoothing control.
- Do not edit `src/weedlib/`, `extensions/inkscape/weedlines.py`,
  `docs/`, or `README.md`.
- New tests go in `tests/test_window_surround.py`. Update the
  mode-list and Start assumptions in `tests/test_window_gate.py`,
  `tests/test_window_return.py`, and `tests/test_window_preview.py`.
  Keep the subject, weed-area, checkerboard, arrow, and background
  checks. If a surround stroke covers a sample, move that sample.
  Do not drop those checks. Offscreen when Qt loads. Skip when
  Qt cannot load. No Inkscape.

## Checks

- With no mode, a blank mode, or `Surround and Conquer`, the
  window opens on that entry. The other three modes still open
  on their entries. An unknown mode opens on frame.
- On a clear design the preview strokes the paths
  `build_surrounds` returns, in the weed-line color, and asks
  again for a distance change, a swap, or entering this mode.
  The distance label, the five percent start, the kept value,
  and the zero floor match the preview part. The other knobs
  do not change the surround.
- A defect paints no surround, does not call `build_surrounds`,
  and leaves Start disabled for every mode.
- Start Algorithm in this mode approves the lines on screen,
  leaves them up, and disables the distance. It does not call
  `generate_weeds`, write a result, or enable Apply. Change
  surround, swap, and a mode change clear that approval.
- A clear design still cuts in frame, grid, and island-hop.
  Island-hop may skip when pyclipper is missing, as
  `tests/test_window_gate.py` already does.
- `QT_QPA_PLATFORM=offscreen pytest tests/test_window_surround.py
  tests/test_window_gate.py tests/test_window_return.py
  tests/test_window_preview.py` passes, or skips only because
  Qt is missing.

## Note

The window mode list is Surround and Conquer, then frame, grid,
and island-hop. A missing mode, a blank mode, or that name in any
case selects Surround and Conquer. `frame`, `grid`, and
`island-hop` still select those entries. Any other value selects
frame.

On a clear design in that mode, the preview strokes the paths
`build_surrounds(subject, distance)` returns, in the weed-line
color, with no fill, above the checkerboard. The distance control
is labeled "Surround distance" and is shown only in this mode,
with Change surround. It starts at five percent of the smaller
side of the design bounds, keeps a value set while the window is
open, and does not go below zero. A distance change, a swap, or
entering the mode asks the library again. Padding, spacing, and
collar do not. A defect paints no surround, does not call
`build_surrounds`, and leaves Start disabled in every mode.

Start Algorithm in this mode approves the lines on screen, leaves
them up, and disables the distance. It does not call
`generate_weeds`, write a result, or enable Apply. Change
surround, swap, and a mode change clear that approval. A weed-line
color change repaints the lines and does not clear it. Frame,
grid, and island-hop still pass the subject to `generate_weeds`
and still cut.

Why: the window still opened on frame and had no surround preview
or approval.

Checked on `master` with `QT_QPA_PLATFORM=offscreen pytest
tests/test_window_surround.py tests/test_window_gate.py
tests/test_window_return.py tests/test_window_preview.py`: 33
passed. Qt loaded. Nothing skipped. No Inkscape.
`src/weedlib/`, `extensions/inkscape/weedlines.py`, `docs/`, and
`README.md` were not edited. Status left `in-progress`.

Summary: No defects. The window opens on Surround and Conquer,
paints the paths `build_surrounds` returns, and Start in that mode
approves those lines without a solver or a result. Frame, grid,
and island-hop still cut.

Context worth keeping: The combo data is Surround and Conquer,
frame, grid, and island-hop. `_opening_mode` selects the first for
a missing mode, a blank mode, or that name in any case. The three
cut tokens match after strip and lower. Any other value selects
the frame entry. The distance spin starts at five percent of the
smaller side of `subject_weed_regions(..., swap=False).bounds`,
keeps that number while the window is open, and does not go below
zero. `_ask_surrounds` calls `build_surrounds(subject, distance)`
only when `blocked` is false and the mode is Surround and Conquer.
Strokes use the weed-line pen, no brush, at z 20. The checkerboard
is z 0. `blocked` is `bool(check.defects)`. Start sets
`surround_approved` and returns before `generate_weeds`, so
`state['result']` stays empty and Apply stays off. Change
surround, swap, and a mode change clear that flag. A weed-line
color change only runs `refresh_preview`. A mode change does not
clear weed lines a cut already drew. Frame, grid, and island-hop
still pass `state['regions'].subject`. Island-hop ran. pyclipper
is installed. `src/weedlib/`, `extensions/inkscape/weedlines.py`,
`docs/`, and `README.md` were not edited. The pass is `cr-01.md`.

Result: No defects remain. The named checks passed.
`QT_QPA_PLATFORM=offscreen pytest tests/test_window_surround.py
tests/test_window_gate.py tests/test_window_return.py
tests/test_window_preview.py` passed: 33 passed, no skips. Qt
loaded. The tests do not start Inkscape.
