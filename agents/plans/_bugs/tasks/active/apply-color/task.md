# Apply color

**Status:** ready

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

The developer writes what changed, why, and how it was checked.
The reviewer then writes the summary, the context worth keeping,
and the result.
