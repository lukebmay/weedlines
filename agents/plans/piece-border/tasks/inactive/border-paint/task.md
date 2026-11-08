# Border paint

**Status:** done

## Goal

The window paints the two rectangles the library
returns, once the figure check is clear. It does not
build them, and it does not wait for Start.

## Do

The paint rules are Piece border in
`agents/architecture/preview.md`. The lengths are
`agents/architecture/boundary.md`. The thread is
`agents/architecture/runtime.md`. Use the spawn that
already asks for a surround. Do not add a second
worker. Do not split these files.

- `extensions/inkscape/weedlines_dialog/__init__.py`
  stores both lengths with the other user-unit lengths.
  Each default is one eighth of an inch under
  `user_unit_scale`, the same scale as the join gap.
  It is not a fixed count of 3.175 or of 6.35.
- `extensions/inkscape/weedlines_dialog/geometry_ask.py`
  asks for the border in the child. The child calls
  `piece_border`. The GUI thread unpacks the plain
  paths and paints them. It does not build or clip
  them. Pass `inner_distance` into `build_surrounds`
  on the surround ask. Pass both lengths into
  `generate_weeds` on the solver ask.
- `extensions/inkscape/weedlines_dialog/inbox.py`
  stores that border reply the way it stores a
  surround reply.
- `extensions/inkscape/weedlines_dialog/preview.py`
  strokes the stored paths in the weed-line color.
  A color change repaints them and does not ask again.
- `extensions/inkscape/weedlines_dialog/run_controls.py`
  puts both lengths on the solver request.
- `extensions/inkscape/weedlines_dialog/form.py` asks
  for the border again on swap, after the new subject
  is stored. Do not add the two option controls. Do
  not invent their labels.

Ask when the figure check is clear, including on open,
without Start. Ask off the GUI thread, because a
length changed or the subject changed, not on a clock.
One ask at a time. Do not paint a result whose subject
or length is already stale. Do not delay the first
subject paint, and do not move the ready callback.

A change to either stored length asks for the border
again. When a surround is showing, a change to the
inner distance also asks for the surround again. A
change to the border width does not. Swap asks for
the border again. The change entry stays callable
without a spin, so the waiting options task can hook
it later.

Do not show the two options. Do not bring back
padding, grid spacing, the collar, or the layer name.
Do not remove island-hop. Do not invent conquer cuts.
Do not edit the library, `docs/`, or `README.md`.

Tests go in `tests/test_window_border.py`. Offscreen
when Qt loads. Skip when Qt cannot load. No Inkscape.
If another window test fails only because a clear
design now starts this ask, update that count. Do not
drop the subject, weed-area, checkerboard, arrow, or
surround checks.

## Checks

- A clear design paints both rectangles without Start,
  in the weed-line color. The child calls
  `piece_border`. The GUI thread does not. A held ask
  still lets the dialog run a timer, and the border
  is not painted until the ask returns.
- With no scale, each length the library receives is
  12. With `user_unit_scale` of one millimeter, each
  is 3.175. Neither case sends 6.35.
- A defect paints no border and does not ask.
- Swap asks again for the new subject. Changing the
  stored inner distance asks for the border and, when
  a surround is showing, for the surround. Changing
  the stored border width asks for the border only.
- The form shows no new length option and no invented
  label. Island-hop is still a mode.
- `QT_QPA_PLATFORM=offscreen pytest tests/test_window_border.py`
  passes, or skips only because Qt is missing.

## Note

The window stores an inner distance and a border width with the
other user-unit lengths. Each default is one eighth of an inch
under `user_unit_scale`, the same scale as the join gap. With no
scale that is 12. With one millimeter it is 3.175. It is not 6.35.

The existing spawn asks for the border when the figure check is
clear, including on open, without Start. The child calls
`piece_border`. This thread unpacks the paths and strokes them in
the weed-line color. It does not build them. A color change
repaints and does not ask again. A held ask still lets a timer
run, and the rectangles wait for the reply. A defect does not ask
and does not paint. The first subject paint and the ready callback
stay where they were. The border ask is the next turn.

One ask at a time. A reply whose subject or length is already
stale is not painted. Swap asks again after the new subject is
stored. `change_piece_length` stays callable with no spin. Either
stored length asks for the border again. When a surround is
showing, the inner distance also asks for the surround. The border
width does not. The surround ask passes `inner_distance`. The
solver ask passes both lengths. The form has no new length option
and no invented label. Island-hop stays a mode.

The border ask is not a run. Start, swap, mode, and colors stay
usable, and a finished result can still Apply. Pause stays visible
so a wait can see the ask. A Start that arrives during the ask
waits, then the follow starts that surround or solver.

`preview.py` names the piece border in the dialog index.
`tests/README.md` has one sentence for `test_window_border.py`.
The library, `docs/`, and `README.md` were not edited.

Why: the library already builds the two rectangles and clips a
surround to the inner one. The window's job is to ask off the GUI
thread and paint the paths it is given, before Start, and to send
the same lengths into the surround and the solver.

Checked with `QT_QPA_PLATFORM=offscreen python3 -m pytest
tests/test_window_border.py tests/test_window_surround.py
tests/test_window_surround_run.py tests/test_window_gate.py
tests/test_window_timing.py tests/test_window_options.py
tests/test_window_preview.py tests/test_window_units.py
tests/test_window_return.py`: 77 passed in 28.55s. No Inkscape.
A surround the clip removes is not painted. The two border
rectangles are not counted as that surround.

Summary: Two defects. The named checks passed. A clear design
paints both rectangles without Start. The child calls
`piece_border`, and this thread does not. A defect does not
ask or paint. No scale sends 12. One millimeter sends 3.175.
Neither sends 6.35. Swap asks again. An inner-distance change
asks for a showing surround. A border-width change does not.
The form has no new length option and no invented label. A
held ask still runs a timer, and the border waits for the
reply. Restart during that ask drops a showing surround.
A solver queued during that ask keeps the subject and the
lengths from the click.

Context worth keeping: The defaults are an eighth of an inch
under `user_unit_scale`, stored with the other user-unit
lengths. The border ask is the next turn after the subject
paint, on the same spawn, one ask at a time. A stale reply
is not painted. `change_piece_length` stays callable with no
spin. The surround ask passes `inner_distance`. The solver
ask passes both lengths when it starts immediately. The
library, `docs/`, and `README.md` were not edited. The pass
is `cr-01.md`. Gate and timing skip every 5-element pen so
the border rectangles are not counted as weed lines.

Result: Two defects remain. Clear `surround_inflight` when
Restart cannot start because a border ask is in flight, so
the follow asks again. Build a queued solver from the
current subject and the current lengths when the follow
starts it, and drop it if the mode has left the mode from
the click. `QT_QPA_PLATFORM=offscreen python3 -m pytest
tests/test_window_border.py tests/test_window_surround.py
tests/test_window_gate.py tests/test_window_timing.py`:
47 passed in 19.23s. No Inkscape. `src/weedlib` was not
edited.

Restart during a border ask clears `surround_inflight`.
The follow asks for the surround again and the window
strokes it. A solver Start during that ask stores the
mode only. The follow builds the request from the current
subject, padding, spacing, collar, inner distance, and
border width. If the mode has left that mode, the follow
drops the request and clears that mode's `cut_started`
flag.

Why: the finished surround tuple still matched, so the
follow treated Restart as already asked. The queued solver
kept the path and the lengths from the click, so a later
swap and a length of 13 never reached `generate_weeds`.

Checked with `QT_QPA_PLATFORM=offscreen python3 -m pytest
tests/test_window_border.py tests/test_window_surround.py
tests/test_window_gate.py tests/test_window_timing.py`:
50 passed in 21.77s. No Inkscape. The library, `docs/`,
and `README.md` were not edited.

Summary: No defects. Restart during a border ask clears
`surround_inflight`, and the follow asks for that surround
again and strokes it. A queued solver stores the mode from
the click. The follow builds the request from the current
subject, padding, spacing, collar, inner distance, and
border width. A mode change drops that request and clears
that mode's `cut_started` flag.

Context worth keeping: The queued value is the mode string,
not a packed path. `_solver_request` reads the subject and
the lengths when the follow starts the ask. After Swap the
keep is 80 by 50, not the 14 by 20 letter from the click.
Padding 7, spacing 9, collar 1.5, and both lengths at 13
are what the solver receives. Frame then grid does not
call the solver, and frame's button reads Start again.
The surround count goes from 1 to 2, and the new path is
a weed-line stroke. The pass is `cr-02.md`. The library
was not edited.

Result: No defects remain. The named checks passed.
`QT_QPA_PLATFORM=offscreen python3 -m pytest
tests/test_window_border.py tests/test_window_surround.py
tests/test_window_gate.py tests/test_window_timing.py`:
50 passed in 21.85s. No Inkscape. `src/weedlib` was not
edited.
