# Library surround

**Status:** done

## Goal

The library builds each surround from the subject and the
surround distance. It does not paint, and it does not choose
the distance.

## Do

- Add `build_surrounds(subject, distance)` in
  `src/weedlib/surround.py`. Export it from
  `src/weedlib/__init__.py`.
- `subject` is the subject `QPainterPath` the window already
  has, in document user units, holes included. `distance` is a
  length in those units and is never negative. Return a list of
  `QPainterPath` values, one outer boundary per cluster. The
  window will stroke those paths. Do not fill them here.
- The geometry is Surround and Conquer in
  `agents/architecture/algorithms.md`. Units are
  `agents/architecture/boundary.md`. This call does not run the
  figure check, does not read SVG, and does not pick a Qt
  binding.
- Do not add a smoothing argument. Do not run the step again
  inside a cluster. Do not emit conquer cuts or lines from a
  surround to the subject.
- Do not edit `src/weedlib/solvers.py` or call its private
  helpers. Do not edit the window, the host, `docs/`, or
  `README.md`.
- Tests go in `tests/test_surround.py`. No Inkscape. Skip when
  Qt cannot load.

## Checks

- Distance zero is the outer boundary of the subject. A loop
  that only follows a hole is not returned.
- A positive distance keeps the surround at least that far from
  the subject, apart from rounding. A straight edge comes back
  as a straight line. A turn is no tighter than the distance.
  A circular arc is allowed. A sharp corner is not.
- Subject pieces whose gap is less than twice the distance
  return one surround. Where those surrounds cross, each
  intersection corner is smoothed and one connector joins those
  two points. A separate connector at each crossing does not
  count. The connector may come closer than the distance. At
  each end, the angle between the connector and the smoothed
  surround is from 45 degrees through 135 degrees. The
  connector does not blend into the surround. Pieces whose gap
  is greater return two.
- An inner corner, such as the reflex corner of an L, is not
  sharp. Its radius is at least the distance.
- The list is only those outer boundaries.
- `pytest tests/test_surround.py` passes without Inkscape.
  `src/weedlib/solvers.py` is unchanged.

## Note

`build_surrounds(subject, distance)` is in `src/weedlib/surround.py`
and exported from `weedlib`. The subject is the region the window
already has, holes included. The distance is a length in those
units. Zero returns each cluster's outer boundary and does not
expand. A positive distance dilates that region with a round join,
once. Each returned path is one closed outer boundary. A loop that
only follows a hole is left out, including when a subject piece
sits in the hole. Pieces merge only when those dilations meet, so
the gap test is the real separation, not an axis gap. There is no
smoothing argument and no second pass inside a cluster.

Qt's boolean ops flatten curves by a fixed amount, which was
pulling round joins and curved subjects inside the distance. The
dilation runs on a copy scaled by 32, with the stroker's curve
threshold at 0.01, then scales back. The stroker is the one from
the binding `weedlib.qt` already chose. `src/weedlib/solvers.py`
is not used and was not edited.

Checked with `pytest tests/test_surround.py`: 3 passed. Qt loaded;
nothing was skipped. No Inkscape. `git diff -- src/weedlib/solvers.py`
is empty.

Review summary: one defect remains. At distance zero,
`build_surrounds` can return a hole. Containment uses the vertices
of `toSubpathPolygons`, and those chords sit inside a curve. On
this Qt, a radius-10 ellipse flattens to 16 vertices and the
deepest chord is at radius 9.802. A triangular hole with a vertex
at radius 9.852 is inside the ellipse and outside that polygon, so
the call returns the ellipse and the triangle. An offset circular
hole of radius 6 with a 0.05 wall at that chord does the same.
Positive distance omits that hole. The round join, the clearance,
and the gap merge held. The suite only locks rectangular holes.

Context worth keeping: dilation scales a copy by 32 and sets the
stroker curve threshold to 0.01. The stroker is the one from
`weedlib.qt`, round join. Clearance on a square and a circle at
distance 2 stayed within about 0.002. A piece in a rectangular
hole stays separate until the dilations meet: gap 7 stays two
surrounds at distance 3 and becomes one at distance 4. Diagonal
circle gaps 3.9 and 4.1 at distance 2 return one and two. Distance
zero keeps curve elements when the subpath count matches. The
caller's path is not mutated. The same chord gap makes
`src/weedlib/figures.py` report a self-overlap for that triangle,
at about (9.603, 1.966) and (9.617, 1.897), and the counter is
dropped from the subject. That is outside this change. The pass
is `cr-01.md`.

Result: one defect remains. The hole check fails for a curved
subject. Remedy: nest closed subpaths by a point the subpath
contains, using `QPainterPath.contains`, and count only a larger
outline. Keep an even depth. Do not use the chord vertices. Do
not call `solvers.py`. Add a distance-zero test whose hole vertex
sits in that chord gap, and expect only the outer path.
`pytest tests/test_surround.py` passed (3 passed, no skips). Qt
loaded. The tests do not load Inkscape. `src/weedlib/solvers.py`
is unchanged. Outside this change, `src/weedlib/figures.py`
calls that triangle a self-overlap. The check is the self-overlap
rule in `agents/architecture/preflight.md`: a closed hole whose
outline does not cross the outer outline is not a self-overlap.
Not fixed here.

Distance zero was nesting closed subpaths from the vertices of
`toSubpathPolygons`. Those chords sit inside a curve, so a hole in
that gap was returned with the outer path. Nesting now uses a point
the subpath contains, tested with `QPainterPath.contains`, and only
a larger outline adds depth. Even depth is still the outer boundary.
Area is the path integral, not the chord polygon. The chord vertices
are not used. `src/weedlib/solvers.py` is not called.

Checked with `pytest tests/test_surround.py`: 4 passed, no skips.
The new distance-zero case puts a triangle vertex 0.05 outside the
deepest chord of a radius-10 ellipse (radius 9.852 on this Qt) and
expects only the outer path. Separately, an offset circular hole of
radius 6 with a 0.05 wall at that chord returns one path at distance
zero and one at distance 1. The caller's path is not mutated. Qt
loaded. The tests do not load Inkscape. `src/weedlib/solvers.py` is
unchanged. The `figures.py` self-overlap on that triangle is still
outside this change.

Review summary: no defects remain. Closed subpaths nest by a point
the subpath contains, tested with `QPainterPath.contains`. Only a
larger outline adds depth. Even depth is the outer boundary. Area
is the path integral, not the chord polygon. The chord vertices are
not used. A hole in the chord gap is omitted, including one that
lies entirely in the gap. The offset circular hole is omitted at
distance zero and at distance one.

Context worth keeping: on this Qt a radius-10 ellipse flattens to
16 vertices and the deepest chord is at radius 9.802. The new test
puts a triangle vertex at radius 9.852 and expects the outer path
only. A triangle with all three vertices in the gap is also
omitted; the point used for it sits at about radius 9.91. An inner
ellipse of radius 6, shifted so the wall is 0.05 at that chord,
returns one path at distance zero and one at distance 1. The
caller's path is not mutated. Distance zero keeps the curve
elements. The ellipse integral is about 314.25, against a chord
area of about 306.22. Dilation still scales a copy by 32 and sets
the stroker curve threshold to 0.01. The stroker is the one from
`weedlib.qt`, round join. An L at distance 2 stayed at least about
1.9998 from the outline. Circle gaps 3.9 and 4.1 at distance 2
return one and two. A curved island of gap 6 stays two surrounds
at distance 2.9 and becomes one at distance 3.1. The rectangular
island of gap 7 stays two at distance 3 and becomes one at
distance 4. `src/weedlib/solvers.py` is not called. The
`figures.py` self-overlap on that triangle stays outside this
change. The pass is `cr-02.md`.

Result: no defects remain. The named checks passed.
`pytest tests/test_surround.py` passed (4 passed, no skips). Qt
loaded. The tests do not load Inkscape. `src/weedlib/solvers.py`
is unchanged.

Where two surrounds cross, the dilation was one outline with a sharp
corner at each crossing: a blend when the pieces overlap, a spike
when they barely meet. Each crossing is now set back and smoothed
with an arc of radius equal to the distance, then one straight
connector joins those two ends. The connector meets each smoothed
arc at a hard angle from 45 degrees through 135 degrees and does not
blend into it. A straight line from one crossing to the other would
cross the gap and come closer than the distance, so each crossing
gets its own connector. Hole nesting is unchanged. A straight edge
stays a straight line, other turns stay smooth, clearance still
holds, and a gap greater than twice the distance stays two surrounds.

Checked with `pytest tests/test_surround.py`: 5 passed, no skips.
The new case merges two squares at edge gaps 3 and 3.9 and on the
diagonal, and expects one surround, a connector at each smoothed
crossing, and an end angle in that range. Qt loaded. The tests do
not load Inkscape. `src/weedlib/solvers.py` is unchanged. An L at
distance 2 still has a 90 degree inner corner in
`src/weedlib/surround.py`. Round join does not fillet that reflex
corner, and it is not a crossing. Clearance there stayed about
1.9998. Not fixed here.

The per-crossing bridges were wrong. Where two surrounds cross,
each intersection corner is smoothed with a turn of radius equal
to the distance, and one connector joins those two points. The
connector may come closer than the distance; that is the overlap
exception. It meets each smoothed surround at a hard angle from
45 degrees through 135 degrees and does not blend into it. The
stroke traverses that one segment twice so both ends stay hard
and the outline stays one closed path. An inner corner, such as
the reflex of an L, gets the same turn, so it is no longer sharp.
The hard angle is only where a connector meets the surround.
Hole nesting is unchanged.

Checked with `pytest tests/test_surround.py`: 6 passed, no skips.
The merge case expects one connector between the two crossings,
not two local bridges, and lets the connector interior come
closer than the distance. The L case expects no sharp inner
corner and a turn radius at least the distance. Qt loaded. The
tests do not load Inkscape. `src/weedlib/solvers.py` is unchanged.

Review summary: two defects remain. A crossing is smoothed and
joined only when both fillets fit. A turn under 20 degrees is
ignored, and a center miss over 0.05 drops the corner. The pair
then keeps the raw corner and draws no connector. Two reflex
corners that sit close stay sharp, because the setback is capped
at 0.45 of the gap between them. The equal-square connector, the
L, and hole nesting held.

Context worth keeping: distance 2. Two 10 by 10 squares at edge
gap 0.5 cross near (10.25, -1.984) and (10.25, 11.984). The
union turn is about -13 degrees, so there is no fillet and no
connector. A 10 by 10 beside a 10 by 4 at gap 3.9 fits one
fillet and fails the other at center error about 0.37. The
failed corner stays a spike of about 18 degrees, and the chord
is dropped. A square beside a circle of diameter 10 fails both
fillets at error about 0.17 and leaves corners of about 44
degrees. A U with a mouth of 6 puts 90 degree corners at
(14, 10) and (16, 10). The radius-2 fillet would fit and stay
outside the dilation, but the cap is 0.9. A mouth of 8 stays
sharp. A mouth of 10 is filleted. Equal squares at gaps 3 and
3.9, and the diagonal pair, keep one connector traversed twice.
The end angles are about 89 to 96 degrees. The midpoint comes
closer than the distance. Other samples stay at least about
1.9998 away. The L arc has radius 2.0 and no corner under about
176 degrees. An island of gap 7 is two surrounds at distance 3
and one at distance 4. The pass is `cr-03.md`.

Result: two defects remain. The connector check fails when the
crossing is shallow or the pieces differ. The inner-corner check
fails when two reflex corners are close. The other named checks
passed on the shapes the suite builds. The suite does not cover
these misses. `pytest tests/test_surround.py` passed (6 passed,
no skips). Qt loaded. The tests do not load Inkscape.
`src/weedlib/solvers.py` is unchanged.

A crossing is smoothed from that pair, including a turn under 20
degrees and a center miss over 0.05, and one connector still joins
the two points. Each end meets the smoothed surround at 45 degrees
through 135 degrees and does not blend into it. The connector may
come closer than the distance. The rest of the surround may not.
Two reflex corners too close for two setbacks become one turn whose
radius is at least the distance. The setback may reach half the gap
between corners, so two fillets meet when that gap allows it.

The old fillet ignored a clockwise turn under 20 degrees and dropped
a corner whose centers missed by more than 0.05, and the pair then
drew no connector. The setback was capped at 0.45 of the gap, so
two close reflex corners stayed sharp.

Checked with `pytest tests/test_surround.py`: 9 passed, no skips.
New cases are two squares at edge gap 0.5, a 10 by 10 beside a 10
by 4 at gap 3.9, a square beside a circle of diameter 10 whose left
side is at x=12, and a U with a mouth of 6. Each crossing case is
one surround and one connector. The U has no sharp inner corner, and
the turn across the mouth has radius at least the distance. That
arc meets the flattened outline on a step shorter than 0.05, and
that step is not the turn. The equal-square, diagonal, L, and hole
cases still pass. Qt loaded.
The tests do not load Inkscape. `src/weedlib/solvers.py` is
unchanged.

Review summary: no defects remain. Gap 0.5, the 10 by 10 beside
a 10 by 4, and the square beside a circle each get one connector.
The shallow turn and the loose center fit are smoothed, not
skipped. The U's close inner corners are one turn, not two sharp
90 degree corners. End angles stay from 45 through 135 degrees,
and the connector does not blend in. Clearance holds except on
that connector. A hole loop is not returned. Straight edges stay
straight.

Context worth keeping: distance 2. Gap 0.5 crosses at about
(10.25, -1.984) and (10.25, 11.984). The union turn is -13.25
degrees. Both ends are tight fillets of radius 2 and setback
0.13. The connector is the vertical segment through those
crossings. Its polyline angles are 91.9 degrees. The midpoint
clearance is 0.25. The unequal pair's lower corner is a tight
fillet of radius 1.995. The upper corner is the loose fillet,
setbacks 2.60 and 3.38, radius 2.003. That corner used to miss
by about 0.37. The tangent angles are 133.4 and 46.6 degrees at
the loose end, and about 92 and 88 at the other. A polyline
chord on the second visit reads 135.4 because the arc step is 4
degrees. The tangent is 133.4. The square beside the circle uses
two loose fillets, radii 1.991 and 2.004, with tangent angles
about 82.5 and 97.5. Its connector midpoint falls inside the
circle. That is the overlap exception. Samples off these
connectors stay at least about 1.992 away. The U's raw corners
are (16, 10) and (14, 10), gap 2, so the half-gap setback is 1
and both fillets fail. One arc replaces them, from (16.496,
21.319) through (14.932, 20.64) to (13.504, 21.319), radius
1.987. No finished vertex remains near the floor. The smallest
vertex angle is 176.1 degrees. Clearance on that arc is 1.99994.
The step onto the flattened outline is shorter than 0.05 and is
not the turn. Equal squares at gaps 3 and 3.9, and the diagonal
pair, keep one connector. Tangent angles are about 86 to 94
degrees. The L arc has radius 2.0 and no corner under 176.1
degrees. A rectangular ring at distance zero is one path. The
island is two paths at distance zero, two at distance 3, and one
at distance 4. The chord-gap triangle at distance zero is the
outer path only. Edge gap 5 and the far diagonal stay two
surrounds. Straight offset sides stay straight. `solvers.py` is
not called. The `figures.py` self-overlap on that triangle stays
outside this change. The pass is `cr-04.md`.

Result: no defects remain. The named checks passed.
`pytest tests/test_surround.py` passed (9 passed, no skips). Qt
loaded. The tests do not load Inkscape. `src/weedlib/solvers.py`
is unchanged.
