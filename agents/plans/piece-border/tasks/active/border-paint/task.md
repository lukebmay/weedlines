# Border paint

**Status:** ready

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

The developer writes what changed, why, and how it was checked.
The reviewer then writes the summary, the context worth keeping,
and the result.
