# Forward radius

**Status:** ready

## Goal

A border corner radius the dialog already has
reaches the library. No radius leaves the calls
unchanged.

## Do

The rule is the algorithms part and the preview
part. Do not copy them. The thread is the runtime
part.

`extensions/inkscape/weedlines_dialog/geometry_ask.py`
builds `_ask_border` and `_ask_surrounds`, and the
child calls `_ask_piece_border`, `_ask_surround`,
and `_ask_solver`.
`extensions/inkscape/weedlines_dialog/run_controls.py`
builds `_solver_request`. When the dialog has a
corner radius, those three library calls receive
it: `piece_border`, `build_surrounds`, and
`generate_weeds`. When it does not, do not pass
one.

Do not edit `form.py`. Do not edit
`tests/test_window_border.py`. The form task owns
both. Do not edit the library. Do not edit the
guide. Do not build or clip a rectangle here.

Put the test in `tests/test_border_ask.py`, and
one index sentence in `tests/README.md`. No
Inkscape. A window, if a test opens one, stays
offscreen. The asks stay off the GUI thread.

## Checks

- With a radius on the dialog, all three library
  calls receive it.
- With no radius, those calls do not receive one,
  and the borders stay square.
- `form.py`, `tests/test_window_border.py`, and
  the library are unchanged.

## Note

The developer writes what changed, why, and how it was checked.
The reviewer then writes the summary, the context worth keeping,
and the result.
