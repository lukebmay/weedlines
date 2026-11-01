# Window timing

**Status:** done

## Goal

The window is on screen before the figure check and before the
surround build. The host still writes the job first. Once the
window is up, it asks for the check, the subject, the weed area,
and the arrow paths.

## Do

- Edit `extensions/inkscape/weedlines_dialog.py`. Today
  `run_weedlines_dialog` calls `classify_figures` and
  `subject_weed_regions` before the dialog exists, and
  `_ask_surrounds` plus `refresh_preview` (which call
  `build_surrounds` and `build_arrow_paths`) before
  `dialog.exec_`. Move those asks to after the dialog is
  visible, and finish them before `ready` is called.
- Use the calls that already exist: `classify_figures`,
  `subject_weed_regions`, `build_arrow_paths`, and
  `build_surrounds`. Do not add a second figure check or a
  second surround builder. Do not edit `src/weedlib/figures.py`,
  `src/weedlib/arrows.py`, `src/weedlib/surround.py`, or
  `src/weedlib/solvers.py`.
- Do not change surround geometry. This task names no method.
- A clear check still paints the surround before the person
  approves it. Start Algorithm still approves that preview and
  does not run a solver. Do not wait for Start before the first
  `build_surrounds`. That fight is open in
  `agents/conflicts.md`. Do not implement either side. Do not
  add conquer or a smoothing control.
- Correction groups stay labeled "Dangling ends", "Figure
  overlaps", and "Self-overlaps". Do not edit
  `extensions/inkscape/weedlines_svg.py`.
- The detached path still writes the job, then starts the host.
  Do not edit `extensions/inkscape/weedlines.py` or
  `extensions/inkscape/weedlines_host.py`. Do not edit `docs/`
  or `README.md`.
- Tests go in `tests/test_window_timing.py`. Keep the paint,
  gate, approval, and cut checks in the window tests named
  below. Change one of those tests only when this order makes
  it look at the preview before the window has asked. Do not
  drop those checks. Geometry tests do not need Inkscape.
  Window tests run offscreen when Qt is available. Skip a
  window test only when Qt cannot load.

## Checks

- `classify_figures` is not called until the Weedlines dialog is
  visible. On a clear Surround and Conquer design,
  `build_surrounds` is not called until that dialog is visible,
  and the surround is painted before Start Algorithm.
- A defect does not call `build_surrounds`. Start stays
  disabled. When `ready` runs, the return line and the
  correction action are already there, and any arrow paths came
  from `build_arrow_paths` after the dialog was visible.
- The subject and the weed area still come from
  `subject_weed_regions`. No new library function classifies
  figures or builds surrounds.
- `src/weedlib/surround.py`, `src/weedlib/figures.py`,
  `extensions/inkscape/weedlines.py`,
  `extensions/inkscape/weedlines_host.py`, and
  `extensions/inkscape/weedlines_svg.py` have no diff. The
  correction group labels are unchanged.
- `pytest tests/test_surround.py` passes without Inkscape.
- `QT_QPA_PLATFORM=offscreen pytest tests/test_window_timing.py
  tests/test_window_surround.py tests/test_window_gate.py
  tests/test_window_return.py tests/test_window_preview.py`
  passes, or skips only because Qt is missing.

## Note

`run_weedlines_dialog` no longer calls `classify_figures` or
`subject_weed_regions` before the dialog exists, and it no longer
calls `build_surrounds` or `build_arrow_paths` before `exec_`.
After the window is visible, and before `ready`, it asks once: one
figure check, one subject and weed area for the current swap, one
`build_surrounds` when that check is clear and the mode is Surround
and Conquer, and one `build_arrow_paths` per defect kind. The
distance is set from those bounds with the spin's signals blocked,
so open does not build the surround twice. A defect still skips
`build_surrounds`, leaves Start disabled, and shows the return line
and the correction action before `ready`. The correction button is
added only in that case; the layout's reparent hides it, so it is
shown again. Later distance, swap, and mode changes still ask
again. There is no new geometry method. The dialog still uses
`classify_figures`, `subject_weed_regions`, `build_arrow_paths`,
and `build_surrounds`.

Why: the window has to be on screen before the figure check and
the surround build, and open must not classify twice or build the
surround twice.

Checked with `pytest tests/test_surround.py`: 9 passed, no
Inkscape. `QT_QPA_PLATFORM=offscreen pytest tests/test_window_timing.py
tests/test_window_surround.py tests/test_window_gate.py
tests/test_window_return.py tests/test_window_preview.py`: 35
passed. Qt loaded. Nothing skipped. The older window tests were
not changed; they look from `ready`, after the asks.
`src/weedlib/surround.py`, `src/weedlib/figures.py`,
`src/weedlib/arrows.py`, `src/weedlib/solvers.py`,
`extensions/inkscape/weedlines.py`,
`extensions/inkscape/weedlines_host.py`, and
`extensions/inkscape/weedlines_svg.py` were not edited. Status
left `in-progress`.

Review summary: no defects remain. The asks run after the window
is visible and before `ready`: one `classify_figures`, one
`subject_weed_regions` for the current swap, one `build_surrounds`
on a clear Surround and Conquer design, and one `build_arrow_paths`
per defect kind. A defect skips `build_surrounds`, leaves Start
disabled, and already shows the return line and the correction
action. Start still approves the painted surround and does not run
a solver. Open does not classify twice or build the surround
twice. No new geometry method. The open fight was not implemented.

Context worth keeping: the asks sit in the existing show timer,
which runs only after `exec_` has shown the dialog. `blocked`
starts true so Start cannot run before the check, then follows
`check.defects`. `_ensure_regions` keeps one subject and weed area
per swap, so the open distance, surround, and preview share that
call. Setting the distance blocks the spin's signals; otherwise
`valueChanged` would build the surround a second time. The
correction button is created only for a defect and inserted into
the return row. A layout reparent after show hides that button, so
it is shown again. `refresh_preview` paints the paths already
built. It does not call `build_surrounds`. The pass is `cr-01.md`.

Result: no defects remain. The named checks passed.
`pytest tests/test_surround.py` passed (9 passed, no Inkscape).
`QT_QPA_PLATFORM=offscreen pytest tests/test_window_timing.py
tests/test_window_surround.py tests/test_window_gate.py
tests/test_window_return.py tests/test_window_preview.py` passed
(35 passed, no skips). Qt loaded. The older window tests were not
edited. Library, host, and SVG files were not edited. Status left
`in-progress`.
