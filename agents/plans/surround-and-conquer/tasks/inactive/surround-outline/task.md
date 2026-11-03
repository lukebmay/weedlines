# Surround outline

**Status:** done

## Goal

Overlapping surrounds are unioned and that whole outline is
smoothed. The join gap joins a near miss. A crossing is not a
connector.

## Do

- Files: `src/weedlib/surround.py`,
  `extensions/inkscape/weedlines_dialog.py`. Edit only the
  library file. `window-start` names both files too, so the two
  tasks do not run together. This one is first.
- `build_surrounds` stays the call the window uses. Add
  `join_gap` with a default of zero, so
  `build_surrounds(subject, distance)` still runs. The dialog
  calls those two arguments today. Do not edit it, and do not
  remove that call.
- The geometry is Surround and Conquer in
  `agents/architecture/algorithms.md`. Units are
  `agents/architecture/boundary.md`. The library does not pick
  the quarter-inch baseline. The window will pass that later.
- Use an efficient method for the union and the smooth. The
  note names that method. A slower method needs a reason. This
  is not a survey task.
- Do not add a smoothing control, conquer cuts, or a second
  surround inside a cluster. Do not edit `src/weedlib/solvers.py`,
  `docs/`, or `README.md`.
- Replace the connector checks in `tests/test_surround.py`:
  `test_crossed_surrounds_join_on_a_connector`,
  `test_shallow_and_unequal_crossings_join_on_a_connector`, and
  `test_square_beside_a_circle_joins_on_a_connector`. A
  connector is not a pass. Keep the checks that still match the
  algorithms part, including holes, straight edges, and inner
  corners. A negative `join_gap` is rejected the same way a
  negative distance is.
- If `tests/test_window_surround.py` or
  `tests/test_window_timing.py` fails only because a sample
  left the outline, move that sample. Do not change when the
  window asks, and do not change the approval checks. Do not
  add a window-timing task.

## Checks

- Overlapping surrounds return one outline. It is smooth, it
  is not a connector between crossings, and it stays at least
  the surround distance from the subject, including at the old
  crossing.
- A join gap of zero leaves a near miss as two surrounds. A
  join gap at least as large as that separation returns one
  smoothed outline, still at least the surround distance from
  the subject.
- `build_surrounds(subject, distance)` still runs.
  `extensions/inkscape/weedlines_dialog.py` has no diff.
- The note names the method.
- `pytest tests/test_surround.py` passes without Inkscape, or
  skips only because Qt cannot load.
- `QT_QPA_PLATFORM=offscreen pytest tests/test_window_surround.py
  tests/test_window_timing.py` passes, or skips only because Qt
  is missing. The ask order is unchanged.
- `src/weedlib/solvers.py` is unchanged.

## Note

Overlaps at a positive distance are one round Minkowski dilation:
`QPainterPathStroker` width `2 * distance`, round join, curve
threshold `0.01`, then the scaled subject united with that stroke.
One stroke of the original subject. A second dilation of the
flattened offset is slow, and a close/open drops a thin neck and
does not keep a straight offset. A near miss is one wider dilation
of radius `distance + join_gap / 2 + 0.01 / 32`. The pad is the
stroker chord in user units. Odd-even components group the outers,
so a piece in a hole stays separate. A straight gap 0.02 below the
separation stays two outlines.

At distance 0 the outers are one winding-fill simplify of the
pieces that meet. A positive join gap then bridges those outers.
Join gap 0 returns each outer. A group of one skips `simplified()`.
`build_surrounds(subject, distance)` still runs. A negative join
gap raises `ValueError`.

Bridges are the external tangents from the closest points. The
walk stops at a reflex, and each outer keeps its own boundary
between the bridges. Convex rings have no reflex, so that tangent
is the hull edge across a step. When a straight offset that does
not face the gap falls inside the tangent, the bridges are the
ends of the facing overlap. A side shorter than 1 counts,
including one stored just under 1, and each end is sampled so a
free stub shorter than the step is tested. The overlap is the
whole colinear run, seam included. Squares `(0, 0, 20, 10)` and
`(0, 10.05, 10, 10)` at distance 0 and join gap 0.1 return area
300.5, with `(15, 10)` on the outline. At distance 2, squares
`(0, 0, 30, 10)` and `(0, 15, 10, 10)` with join gap 1 keep
`(20, 12)` on the outline and leave `(20, 18)` outside.
Rectangles `(0, 0, 30, 10)` and `(0, 10.05, 29.2, 0.9)` at
distance 0 and join gap 0.1 return area 327.74, and `(29.6, 10.3)`
stays outside. At distance 2, `(0, 0, 30, 10)` and
`(0, 15, 29.2, 0.5)` with join gap 1 leave `(29.6, 12.5)`
outside. Squares `(0, 0, 10, 10)`, `(10.05, 0, 10, 10)`, and
`(4, 10.05, 10, 10)` return area 301. The run bridges from
x = 4 to x = 14, and `(12, 10.02)` is inside. A tangent is kept
only when each ring has two distinct bridge ends. One shared
vertex drops that ring, so the bridges are the facing overlap.
Squares `(0, 0, 30, 10)`, `(0, 10.05, 10, 10)`, and
`(20, 10.05, 10, 10)` at distance 0 and join gap 0.1 return area
501, with `(15, 10)` on the outline, `(15, 15)` outside, and
`(5, 5)` inside. The shorter right piece at
`(14.95, 10.05, 15.05, 2)` returns area 431.3525. `(12, 10)`
stays on the outline, `(5, 5)` stays inside, and `(12, 12)`
stays outside. An overlap is not a bridge when one ring sits
inside the other. A 40 square with a hole from (10, 10) to
(30, 30) and one piece at (17, 17, 6, 6) is 7 from the hole
wall. At distance 2, join gap 2.99, 3, and 6.35 stay two
outlines. `(20, -2)` stays on the frame. `(23, 6.5)` stays off
the outline. `(15, 20)` stays on the piece. At distance 0,
join gap 6.35 and join gap 7 stay two outlines, areas 1600 and
36. A square at `(45, 0, 10, 10)` with join gap 6.35 joins the
frame: `(57, 5)` and `(20, -2)` stay on that outline, and
`(42.5, 5)` stays inside. The piece stays the other outline.
Clearance stays at least the distance, within 0.01.

Inner rings bridge each other when neither sits inside the
other and the separation is at most the join gap. Each new
edge is judged whole. The bridge is dropped when that edge
meets the subject or comes closer than the surround distance.
The limit is the distance minus 0.01. The gap is the distance
from the closed edge to each subject line, quad, and cubic,
not the chords of `toSubpathPolygons`. On a cubic the closest
point is a root of `(C - P) · C'`, a quintic split by its
derivative. A tangent parallel to the edge is a quadratic,
and a crossing is a cubic. A straight tangent uses the
parallel span instead of an isolated root. Samples are not
used. On a radius-10 circle the deepest chord sits 0.198
inside the curve. The edge from `(13.197260, -5.488972)` to
`(10.030895, 10.194590)` is 1.848 from that circle and 2.048
from the chord. At distance 2 the curve rejects it. An edge
at gap 2 still clears. A frame `(0, 0, 80, 80)` with hole
`(10, 10, 60, 60)` and pieces `(17, 17, 4, 4)` and
`(25.5, 17, 4, 4)` at distance 2 stays two outlines at join
gap 0.5 and 6.35. The piece outline has area 128.5686, and
`(23.25, 19)` lies inside it. At distance 0, pieces
`(17, 17, 2.95, 2.95)` and `(20.05, 17, 2.95, 2.95)` in the 40
frame stay areas 1600 and 17.7 at join gap 6.35 and 7. Pieces
20 apart at join gap 6.35 stay three outlines. A full-height
wall of thickness 1, and two separate holes, stay three
outlines. A finger of the frame between the pieces stays
three outlines too. At distance 0, squares `(0, 0, 10, 10)`
and `(16.35, 0, 10, 10)` with finger `(12.05, 8, 1, 12)` stay
three outlines at join gap 6.34 and 6.35. `(12.5, 10)` stays
off those outlines. At distance 2, squares `(0, 0, 10, 10)`
and `(40, 0, 10, 10)` with finger `(20, 11, 1, 19)` stay three
outlines at join gap 25.9 and 26. `(20.5, 12)` stays off those
outlines. Join gap 7 and join gap 100 stay three outlines too.
Without the finger the same pieces join. The step stays those
gap edges. A surround-distance arc does not fit: the gap is
shorter than the setback, and the arc enters the pocket.

Colinear straight offsets become one line before the fillet, when
that line stays outside the offset. The anchor is a straight
side, including one shorter than 1. A dent of 0.015 is the same
dip. Five squares at x = 0, 13, 26, 39, and 52 keep `y = 12`
across the gaps. Gap 3.9 does too. Gap 0.5 keeps `(10.25, 12)`
on the line. Rectangles `(0, 0, 0.9, 10)` and `(1.4, 0, 0.9, 10)`
at distance 2 keep `(1.15, 12)` on that line, and the outer
corner stays on the arc. A mouth on one dilation is still one
arc. A fillet at each crossing was the bump: the line was
already clear.

The stepped squares at join gap 0.1 stay area 175. The stepped
union plus the square at `(-10.05, 0)` stays area 275.5, and
`(2, 12)` stays outside. The L upright stays on `x = 12`.

Review accepted. No defect. The edge from `(13.197260,
-5.488972)` to `(10.030895, 10.194590)` is 1.848 from the
radius-10 cubics and 2.048 from the chords. At distance 2 it
is rejected. Gap 2.000 still clears. Gap 1.98 is rejected and
gap 1.995 clears, so the limit stays the distance minus 0.01.
The same rings join when that circle is far. Endpoint contact
at distance 0 is not a hit. Nothing routes around the finger.
Shelves, colinear offsets, the piece inside a frame, inner
pairs, and the distance-0 unions still hold. No sampled
outline point was inside the surround distance.

Checked: `pytest tests/test_surround.py` was 24 passed.
`QT_QPA_PLATFORM=offscreen pytest tests/test_window_surround.py
tests/test_window_timing.py` was 15 passed. Qt loaded. No
Inkscape. No window sample moved. The ask order is unchanged.
The dialog and `src/weedlib/solvers.py` have no diff.
`build_surrounds(subject, distance)` still runs. A negative
join gap raises `ValueError`.
