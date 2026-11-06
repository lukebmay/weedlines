# Apply color

**Status:** done

## Goal

The two Apply color checks pass. The dialog returns the
weed-line color the tests ask for, or the tests match what
the guide says Apply returns on Surround and Conquer.

## Do

Confirmed on `d08fccd`, before the figure-check spawn:
`tests/test_cut_stroke.py::test_untouched_apply_returns_the_initial_color`
fails with `assert None == '#FF0000'`.
`tests/test_cut_stroke.py::test_apply_returns_the_changed_weed_line_color`
fails with `assert None == '#00AA00'`. Start on the default
Surround and Conquer mode paints a surround and leaves Apply
disabled, so the dialog returns `(None, None, None)`.

Make those two checks pass. The guide is the product. Do
not edit the guide. Stop and return if the fix would change
what Apply returns, or what the surround step writes.

Do not move the figure check, the surround, or the solvers
off their current thread or process. Do not add conquer.

## Checks

`pytest tests/test_cut_stroke.py tests/test_window_preview.py`
with no Inkscape. Skip the window if Qt cannot load.

- The two Apply color checks pass.
- The other cut-stroke checks still pass.
- A surround preview test that locks the painted surround
  still matches.

## Note

The two color checks open on frame. Start there runs the solver,
and Apply returns the weed-line color with the cuts. An untouched
control is `#FF0000`. A committed `#00aa00` is `#00AA00`. The path
is not empty, and the layer is `Weed lines`.

Why: the window opens on Surround and Conquer. Start there paints
a surround and does not enable Apply, so the dialog returns
nothing. Enabling Apply, or having that step call the solver,
would change what Apply returns or what the surround step writes.
Frame is a mode that returns cuts. The dialog and the surround
step were not edited.

Checked with `QT_QPA_PLATFORM=offscreen pytest
tests/test_cut_stroke.py tests/test_window_preview.py`: 20 passed
in 3.45s. Qt loaded. No Inkscape. Status left `in-progress`.

Review summary: no defect remains. The two color checks open
on frame, still require the weed-line color, and reject an
empty path. The dialog and the surround step were not edited.
The pass is `cr-01.md`.

Context worth keeping: `_run_dialog` forwards `defaults`. The
color checks pass `{'mode': 'frame'}`. A call that omits
defaults still opens on Surround and Conquer, and the closed
window still returns `(None, None, None)`. Apply enables only
when the solver path is present and not empty. The driver
rejects the window if Apply stays disabled, so None cannot
pass as a color. The untouched check requires `#FF0000`, the
layer `Weed lines`, and a non-empty path. The changed-color
check requires `#00AA00` and a non-empty path, and discards
the layer. The surround lock is not in the named files. It is
`test_clear_design_strokes_surrounds_and_follows_distance` and
`test_start_paints_without_a_solver_or_a_result` in
`tests/test_window_surround.py`. Those two passed. Apply stays
disabled there, and the second returns `(None, None, None)`.

Result: No defect remains. The named checks passed.
`QT_QPA_PLATFORM=offscreen pytest tests/test_cut_stroke.py
tests/test_window_preview.py` passed (20 passed in 2.35s).
Qt loaded. Nothing skipped. The tests did not start Inkscape.
`git diff --exit-code` is empty for
`extensions/inkscape/weedlines_dialog.py`,
`src/weedlib/surround.py`, and `src/weedlib/solvers.py`.
The two surround lock tests passed (2 passed in 0.61s).
