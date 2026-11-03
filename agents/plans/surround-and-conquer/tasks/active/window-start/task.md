# Window start

**Status:** ready

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

The developer writes what changed, why, and how it was checked.
The reviewer then writes the summary, the context worth keeping,
and the result.
