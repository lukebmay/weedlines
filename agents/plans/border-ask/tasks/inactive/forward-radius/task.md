# Forward radius

**Status:** done

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

`lengths['corner_radius']` is the stored radius, in user
units the caller already converted. When that value is
set, `_ask_border`, `_ask_surrounds`, and
`_solver_request` put it on the request. The child then
passes `corner_radius` to `piece_border`,
`build_surrounds`, and `generate_weeds`. When the key is
absent, those three calls stay as they were and the
borders stay square. Zero is passed through. A change of
the stored value makes the border and the surround
stale, so the next ask uses the new number. The child
still runs in the spawn worker. This ask does not read
a scale and does not build the rectangles.

Why: the library already rounds both rectangles, and
both clips follow that inner border, only when the call
receives the radius. The dialog was still omitting it.

Checked with `python3 -m pytest tests/test_border_ask.py`:
2 passed. No Inkscape. Qt loaded for the path objects.
The test does not open a window.

The form does not store the key yet.
`extensions/inkscape/weedlines_dialog/form.py`
`_on_piece_length` returns when the key is not `inner`
or `border`, so `change_piece_length('corner_radius')`
does not ask. That file was left alone. Store the
radius on `lengths['corner_radius']` only while
rounded corners are on.

Summary: No defect in this change. When
`lengths['corner_radius']` is set, `_ask_border`,
`_ask_surrounds`, and `_solver_request` put it on the
request, and the child passes it to `piece_border`,
`build_surrounds`, and `generate_weeds`. When the key
is absent, those calls omit it and the borders stay
square. Zero is passed through. A missing key is not
zero. A change of the stored value makes the border
and the surround stale. The parent only builds the
request. `_begin_ask` still spawns the worker.

The form report is confirmed, and it is not a defect
here. `form.py` `_on_piece_length` returns unless the
key is `None`, `inner`, or `border`, so
`change_piece_length('corner_radius')` does not ask.
The form does not store the key. That is already
`agents/plans/piece-border/tasks/active/border-options/task.md`.
That task owns `form.py` and
`tests/test_window_border.py`. It says the radius calls
`change_piece_length` and the value is kept while the
window is open, including while the box is off. It is
allowed to close this. It must not edit the ask.
Storing the radius on `lengths['corner_radius']` only
while the box is on would drop the kept number if that
key is the only copy. The preview keeps the number
while the window is open. The radius applies only while
the box is on. This ask forwards the key whenever it
is set. Keeping the number and applying it are not the
same.

Context worth keeping: The ask does not read a scale
and does not build the rectangles. `form.py`,
`tests/test_window_border.py`, and the library were
not edited. `tests/README.md` has one sentence for
`tests/test_border_ask.py`. The new test does not open
a window and does not start the worker. The thread
rule holds because `_begin_ask` is unchanged. The pass
is `cr-01.md`.

Result: No defect. `python3 -m pytest tests/test_border_ask.py`:
2 passed in 0.07s. PyQt6 6.7.1. No Inkscape. The form
report is confirmed and was not fixed. It is the form
task, not a gap that task cannot close.
