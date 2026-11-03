# Window start

**Status:** done

## Goal

The person starts the surround. The window then asks
`build_surrounds` and passes the join gap. Until that start it
paints none.

## Do

- Files: `src/weedlib/surround.py`,
  `extensions/inkscape/weedlines_dialog.py`. Edit the dialog,
  not the library. `surround-outline` names both files too, so
  the two tasks do not run together. That task is first. If
  `build_surrounds` does not accept `join_gap`, stop. Do not
  add the argument here.
- Call `build_surrounds(subject, distance, join_gap)`. Do not
  add another builder. Do not ask for a surround, and do not
  paint one, until Start Algorithm. Setting the initial
  distance and join gap is not that ask. The behavior is
  Surround preview in `agents/architecture/preview.md`. The
  baseline is in `agents/architecture/boundary.md`.
- The window is already shown before the figure check. Do not
  move `classify_figures` in front of the dialog. Do not create
  or reopen `window-timing`.
- After Start, ask again when the distance changes, when the
  join gap changes, when the person swaps, and when the mode
  becomes Surround and Conquer again. Change surround clears
  the lines and does not ask until the next Start. Leaving the
  mode clears them. The values the person set stay. Start does
  not call `generate_weeds`, does not write a result, and does
  not enable Apply. A weed-line color change repaints and does
  not clear the lines.
- Show the join gap only in this mode. The label is
  `Join gap (mm)`, the same millimetre marking as
  `Padding (mm)`. The object name is `join-gap`. Until the
  person sets it, pass 6.35. Do not allow it below zero. Leave
  the surround distance labeled `Surround distance`.
- A defect still does not call `build_surrounds`. Start stays
  disabled for every mode. Frame, grid, and island-hop still
  cut. Do not add conquer, a second surround, or a smoothing
  control.
- Update `docs/user/surround.md` in this same change. The tone
  is `agents/installed/documentation.md`. The steps follow the
  wait, the two lengths, Start, and Change surround. Do not
  call Start an approval. When the line under the preview names
  problems, no surround is shown and Start stays off; point at
  `docs/user/correction-arrows.md`. Do not edit that page. Do
  not edit `README.md`. The default-mode sentence is still
  true.
- Update `tests/test_window_surround.py` and
  `tests/test_window_timing.py`. The timing test expects a
  surround before Start. Change that expectation. Keep the
  check that the dialog is visible before `classify_figures`.
  The wrappers take `(subject, distance)` today; accept
  `join_gap`. Edit `tests/test_window_gate.py`,
  `tests/test_window_return.py`, or
  `tests/test_window_preview.py` only when a check would
  otherwise look at the surround before Start. Do not drop
  their checks.

## Checks

- On a clear Surround and Conquer design, `build_surrounds` is
  not called until Start Algorithm, and the dialog is already
  visible before `classify_figures`. Start passes the subject,
  the distance, and the join gap, and the preview strokes those
  paths in the weed-line color, with no fill. It does not call
  `generate_weeds`, write a result, or enable Apply.
- Before Start, changing the distance or the join gap does not
  call `build_surrounds`. After Start, a distance change, a
  join gap change, a swap, and entering this mode again each
  call it. Change surround clears the strokes and does not call
  it. The spin values stay.
- The join gap label is `Join gap (mm)`, shown only in this
  mode, starting at 6.35, and it does not go below zero. The
  distance label is still `Surround distance`.
- A defect paints no surround, does not call
  `build_surrounds`, and leaves Start disabled for every mode.
- A clear design still cuts in frame, grid, and island-hop.
- `docs/user/surround.md` follows that order and does not call
  Start an approval. `README.md`,
  `docs/user/correction-arrows.md`, and
  `src/weedlib/surround.py` have no diff from this task.
- `pytest tests/test_surround.py` passes without Inkscape.
- `QT_QPA_PLATFORM=offscreen pytest tests/test_window_timing.py
  tests/test_window_surround.py tests/test_window_gate.py
  tests/test_window_return.py tests/test_window_preview.py`
  passes, or skips only because Qt is missing.

## Note

The window waits. On a clear Surround and Conquer design,
`build_surrounds` is not called while the spins are set, while
the mode changes, or while the person swaps, until Start
Algorithm. Start calls `build_surrounds(subject, distance,
join_gap)` and strokes those paths in the weed-line color with
no fill. It does not call `generate_weeds`, write a result, or
enable Apply. After that, a distance change, a join gap change,
a swap, and entering this mode again each call it. Change
surround clears the strokes, keeps both spin values, and does
not call again until the next Start. Leaving the mode clears
the strokes and keeps the values. A weed-line color change
repaints and does not clear the lines. The join gap control is
`join-gap`, labeled `Join gap (mm)`, shown only in this mode,
starting at 6.35, and it does not go below zero. The distance
label is still `Surround distance`. A defect still skips
`build_surrounds` and leaves Start disabled for every mode.
Frame, grid, and island-hop still cut. `docs/user/surround.md`
follows the wait, the two lengths, Start, and Change surround,
and it does not call Start an approval.

Why: the window was painting a surround before the person
started that step, and the call did not pass the join gap.

Checked with `pytest tests/test_surround.py`: 24 passed, no
Inkscape. `QT_QPA_PLATFORM=offscreen pytest
tests/test_window_timing.py tests/test_window_surround.py
tests/test_window_gate.py tests/test_window_return.py
tests/test_window_preview.py`: 35 passed. Qt loaded. Nothing
skipped. There is no live Inkscape window. The gate, return,
and preview tests were not edited; they do not look at a
surround before Start, and their checks still pass.
`src/weedlib/surround.py`, `README.md`, and
`docs/user/correction-arrows.md` were not edited. Status left
`in-progress`.

Summary: No defects. The window does not ask for a surround
until Start Algorithm. Start calls `build_surrounds(subject,
distance, join_gap)` and strokes those paths. It does not run a
solver, write a result, or enable Apply.

Context worth keeping: `surround_started` stays false until
Start in Surround and Conquer. `_ask_surrounds` returns unless
that flag is set, the check is clear, and the mode is still
Surround and Conquer. Setting either spin is not an ask.
`refresh_preview` strokes `surround_paths` only under that same
condition, with the weed-line pen and no brush, at z 20. The
checkerboard is z 0. Start sets the flag, asks, and returns
before `generate_weeds`, so `state['result']` stays empty and
Apply stays off. A distance change, a join gap change, and a
swap ask only when the flag is set. Leaving the mode clears
`surround_paths` and keeps the flag, so coming back asks again.
Change surround clears the flag and the paths, so a later mode
round trip does not ask until the next Start. Both spins stay
enabled and keep their values. The join control is `join-gap`,
labeled `Join gap (mm)`, range floor 0, initial `_JOIN_GAP`
6.35, shown only in this mode. The distance label is still
`Surround distance`. `blocked` is `bool(check.defects)`, and
Start stays disabled in every mode while it is set. The figure
check still runs from the zero-timer after `exec_` has shown
the window. Frame, grid, and island-hop still pass
`state['regions'].subject` to `generate_weeds`. Island-hop ran.
pyclipper is installed. `src/weedlib/surround.py`, `README.md`,
and `docs/user/correction-arrows.md` have no diff. The pass is
`cr-01.md`.

Result: No defects remain. The named checks passed.
`pytest tests/test_surround.py`: 24 passed. No Inkscape.
`QT_QPA_PLATFORM=offscreen pytest tests/test_window_timing.py
tests/test_window_surround.py tests/test_window_gate.py
tests/test_window_return.py tests/test_window_preview.py`: 35
passed, no skips. Qt loaded. The tests do not start Inkscape.
