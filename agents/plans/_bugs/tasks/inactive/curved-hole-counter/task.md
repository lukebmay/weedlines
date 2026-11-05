# Curved hole counter

**Status:** done

## Goal

A closed hole whose outline does not cross the outer outline
stays the counter. It is not a self-overlap.

## Do

- The miss is in `src/weedlib/figures.py`. The border test uses
  chord vertices from `toSubpathPolygons`. On a radius-10
  ellipse those chords sit inside the curve. A triangular hole
  with a vertex between the curve and a chord is reported as
  two self-overlaps, and the counter is dropped.
- Follow the self-overlap rule in
  `agents/architecture/preflight.md`. Do not edit that file.
- Add the regression in `tests/test_figures.py`. No Inkscape.
  Skip when Qt cannot load.
- Do not edit the surround module, the window, or the host.

## Checks

- That ellipse and triangle return no self-overlap. The hole
  stays the counter: the subject keeps both rings, and the
  triangle's centroid is weed.
- The same triangle moved inward so it clears the chords still
  returns no self-overlap.
- `pytest tests/test_figures.py` passes without Inkscape.
- Neighboring pieces that cross are a self-overlap. The line
  from (0, 0) to (10, 0) and the following cubic
  (10, 0), (10, 5), (0, -5), (0, 2) are reported. A cubic
  that only meets the line at the joint is not a
  self-overlap. A shared endpoint is not a crossing.
- A line that touches a cubic and does not change sides is
  not a self-overlap. The cubic (0, 0), (0, 3), (3, 3),
  (3, 0) and the line at y=2.25 are not a self-overlap. The
  line at y=2.05 stays two self-overlaps. The flat
  inflection through (0.5, 0) stays one self-overlap.
- Two curves that only touch are not a self-overlap. A
  radius-10 circle and a radius-3 circle centered 7 units
  out along y=x, meeting within 1e-10, return no
  self-overlap. This test does not require that hole to be
  the counter. That miss is `touching-hole-counter`.
- A straight cubic, control points on the line between its
  ends, crosses when the line through those ends crosses.
  The hump (0, 0), (0, 3), (3, 3), (3, 0) and the straight
  cubic (-1, 2.05), (1, 2.05), (2, 2.05), (4, 2.05) are
  two self-overlaps near (0.849, 2.05) and (2.151, 2.05).
  The cubic (0, -1), (3, -1), (7, 1), (10, 1) and the
  straight cubic (0, 0), (0.2, 0), (0.4, 0), (10, 0) are
  one self-overlap at (5, 0). y=2.25 stays no self-overlap.
- The flat inflection through (0.5, 0) stays one
  self-overlap when the crossing piece is the even straight
  cubic through the same ends, from (-0.2, 0) to (1.2, 0).
- An uneven cubic just off that segment is a self-overlap
  where the segment crosses. The hump (0, 0), (0, 3),
  (3, 3), (3, 0) and (-1, 2.05), (1, 2.0501), (2, 2.0499),
  (4, 2.05) are two self-overlaps near (0.849, 2.05) and
  (2.151, 2.05). y=2.25 stays none. A radius-10 ellipse
  and (-12, 1), (-11.5, 1.01), (-11, 0.99), (12, 1) are
  two self-overlaps, one near (-9.950, 1.001) and one near
  (9.951, 0.999).
- Two curves that are not flat and that change sides are a
  self-overlap even when the samples are below 1e-9. The
  inflection (0, -0.125), (1/3, 0.125), (2/3, -0.125),
  (1, 0.125) and (0, 0), (1/3, 5e-6), (2/3, -5e-6), (1, 0)
  are one self-overlap at (0.5, 0). The tangent circles
  stay no self-overlap.
- A collinear cubic that runs past its ends is a
  self-overlap where another curve crosses that extra
  length. (0, 0), (-1, 0), (2, 0), (1, 0) and
  (0.6, -0.4), (1.4, -0.3), (0.9, 0.2), (1.6, 0.5) are
  one self-overlap near (1.146, 0). The same pair with
  the open cubic (0, 0), (-1, 1e-6), (2, -1e-6), (1, 0)
  is still one self-overlap near (1.146, 0). A bow of
  2e-6 and a bow of 3e-6 stay one. A crossing at x=1.5
  is past the curve and stays none. The hump against
  y=2.25 stays none.

## Note

The border test in `src/weedlib/figures.py` took its vertices from
`toSubpathPolygons`. On a curve those chords sit inside the outline,
so a closed hole in that gap was two self-overlaps and was not
subtracted as the counter.

Crossings now use the path's lines and curves. A line meets a cubic
from the cubic polynomial. Two cubics count only after each chord is
within 1e-6 of its curve. A cubic that crosses itself is still one
point. The painted close of an open subpath is still not a border.
The piece walk lives in `figures.py`. The surround module already
has a private walker, and that module is out of scope, so the callers
there were not converted.

`tests/test_figures.py` places a triangle in the chord gap of a
radius-10 ellipse, and the same triangle with its vertex at radius
9. Both return no defect. The figure and the subject each keep both
rings. The triangle centroid is weed, and the ellipse center is
subject.

Checked with `pytest tests/test_figures.py` (15 passed). Qt loaded.
Nothing was skipped. No Inkscape.

Review summary: three defects remain in the change. The named
checks passed. The radius-10 ellipse and the triangle in the
chord gap are one figure, the outlines do not cross, and there
is no self-overlap. The counter, the hole of the figure, stays.
The figure and the subject each keep the outer outline and the
counter. The triangle centroid is weed area. The ellipse center
is subject. The triangle at radius 9 is the same result. A touch
is still a self-overlap: a line at the peak of a cubic, and two
circles that only meet. Neighboring pieces that cross are not a
self-overlap. The pass is `cr-01.md`.

Context worth keeping: the border pieces are the path's lines and
cubics, not `toSubpathPolygons`. The painted close of an open
subpath is not a piece. A line meets a cubic from the polynomial.
Two cubics split until each chord is within 1e-6, or depth 32.
That flatness still reports a touch. The circle pair meets within
1e-10 at about (7.071, 7.071) and is reported near (7.073, 7.069)
and (7.069, 7.073). The old chord test reported none. A root
counts as a crossing only when the curve changes sides. The
inflection through (0.5, 0) must stay one self-overlap.
`_self_overlap_defects` skips adjacent pieces, so the line
(0, 0)-(10, 0) and the following cubic that crosses near
(0.51, 0) and (4.36, 0) are only dangling ends. A shared endpoint
is already dropped. The deepest ellipse chord is near radius
9.80. The gap vertex crosses that ring twice. Radius 9 does not.
A cubic that crosses itself is one self-overlap. The suite does
not lock that. A line through the ellipse joints at y=0 is not a
self-overlap. The line at y=1 is. The surround module, the
window, the host, and the guide were not edited.

The touching circles are also not the counter, for an older
reason. `inner.subtracted(outer).simplified()` is a triangle of
area about 0.003 that still lies in the outer fill.
`_painted_parts` then leaves the inner center subject, not weed
area. A radius-3 circle centered 6 units out, with a gap, does
stay the counter. That failure is outside this change. Do not
use the touching circles' counter as the proof of the border fix.

Result: three defects remain in the change. One bug is outside
it. The named checks passed. `pytest tests/test_figures.py`
passed (15 passed, not skipped). Qt loaded. No Inkscape.

Neighboring pieces are compared in `_self_overlap_defects`. A
shared endpoint is still dropped, so a cubic that only meets
the line at the joint is not a self-overlap. `_line_cubic_hits`
counts a root only when the cubic changes sides of the line.
A touch stays out. A flat inflection still counts once.
`_cubic_pair_hits` counts a pair only when each curve changes
sides. `_painted_parts` was not changed.

The regressions are in `tests/test_figures.py`. The line from
(0, 0) to (10, 0) and the cubic (10, 0), (10, 5), (0, -5),
(0, 2) are two self-overlaps, near (0.51, 0) and (4.36, 0).
Two neighboring cubics that cross are one. The hump against
y=2.25 is none, y=2.05 is two, and the inflection through
(0.5, 0) is one. The radius-10 circle and the radius-3
circle centered 7 units out along y=x meet within 2e-10 and
are not a self-overlap. That test does not require the
counter.

Checked with `pytest tests/test_figures.py` (18 passed). Qt
loaded. Nothing was skipped. No Inkscape. The touching
circles are still not the counter. That remains
`touching-hole-counter`.

Review summary: two defects remain in the change. The named
checks passed. A straight cubic is a curve piece whose
control points lie on the line between its ends. When that
piece crosses another piece of the figure, the figure check
does not report a self-overlap. The line through the same
ends does. Uneven control points sample the wrong place on
the curve. Even control points at a flat inflection are
sampled at the right place, and a side change smaller than
1e-9 is dropped. The tangent circles stay no self-overlap.
The pass is `cr-02.md`.

Context worth keeping: a flat cubic has to use
`_line_cubic_hits` on its endpoints. Projecting the chord
point fixes the uneven line and leaves the inflection
broken. Deleting the 1e-9 floor fixes the inflection and
leaves the uneven line broken. The hump (0, 0), (0, 3),
(3, 3), (3, 0) and the straight cubic (-1, 2.05), (1, 2.05),
(2, 2.05), (4, 2.05) cross near (0.849, 2.05) and
(2.151, 2.05). The figure check reports none. The line
reports both. The fraction 0.37 along that cubic sits near
x=0.91; the curve parameter of the crossing is about 0.357.
y=2.25 stays none. The cubic (0, -1), (3, -1), (7, 1),
(10, 1) crosses (0, 0), (0.2, 0), (0.4, 0), (10, 0) at
(5, 0) and is reported only as a line. The inflection
against an even straight cubic from (-0.2, 0) to (1.2, 0)
is none; the line is one at (0.5, 0). Sides there are about
1e-12. The tangent-circle samples are the same sign, about
1e-6. The hump against y=2.25 is the same sign, about 1e-7.
The touching circles still meet within about 1.1e-10. The
inner center is subject and is not weed area. The radius-3
circle centered 6 units out is the counter: its center is
weed area. That remains `touching-hole-counter`.
`_painted_parts` was not changed. The surround module, the
window, the host, and the guide were not edited.

Result: two defects remain in the change. The named checks
passed. `pytest tests/test_figures.py` passed (18 passed,
not skipped). Qt loaded. No Inkscape.

A straight cubic whose controls lie on the segment between its
ends is that segment. `_cubic_pair_hits` sends the segment
through `_line_cubic_hits`, and through `_proper_cross` when
both cubics are straight. The chord fraction is not used. The
1e-9 side floor is unchanged, so a same-sign touch stays out.

The hump (0, 0), (0, 3), (3, 3), (3, 0) and the straight cubic
(-1, 2.05), (1, 2.05), (2, 2.05), (4, 2.05) are two
self-overlaps near (0.849, 2.05) and (2.151, 2.05). y=2.25 is
none. The cubic (0, -1), (3, -1), (7, 1), (10, 1) and
(0, 0), (0.2, 0), (0.4, 0), (10, 0) are one self-overlap at
(5, 0). The inflection through (0.5, 0) against the even
straight cubic from (-0.2, 0) to (1.2, 0) is one.
`_painted_parts` was not changed, so the touching circles'
counter stays `touching-hole-counter`. The surround module,
the window, the host, and the guide were not edited.

Checked with `pytest tests/test_figures.py` (20 passed). Qt
loaded. Nothing was skipped. No Inkscape.

Review summary: three defects remain in the change. The named
checks passed. A straight cubic whose controls lie on the
segment between its ends is that segment, and those crossings
are self-overlaps. A touch that stays on one side is not. The
same crossing is missed when the controls leave that segment.
The 1e-9 side floor still drops a crossing of two curves that
are not flat. A collinear cubic that runs past its ends is not
a self-overlap where another curve crosses that extra length.
The pass is `cr-03.md`.

Context worth keeping: `_cubic_pair_hits` sends a cubic through
`_line_cubic_hits` only when both controls are within 1e-9 of
the segment and project onto it. Two such cubics use
`_proper_cross`. The chord fraction is not used on that path,
and the side floor is not used there. Outside the band,
`_cubics_change_sides` still samples at the chord fraction.
The hump (0, 0), (0, 3), (3, 3), (3, 0) and (-1, 2.05),
(1, 2.0501), (2, 2.0499), (4, 2.05) cross near (0.849, 2.05)
and (2.151, 2.05). The figure check reports none. Controls on
y=2.05 report both. A bow of 1e-9 is already none. y=2.25 with
the same 1e-4 bow stays none. The radius-10 ellipse and
(-12, 1), (-11.5, 1.01), (-11, 0.99), (12, 1) are one
self-overlap, near (9.951, 0.999). The one near
(-9.950, 1.001) is missing. Those samples are the same sign,
about 1 apart. Projecting the chord point onto the curve
reports both, and it does not fix the floor. Widening the
straight test to 1e-6 fixes neither figure.

The inflection (0, -0.125), (1/3, 0.125), (2/3, -0.125),
(1, 0.125) and (0, 0), (1/3, 5e-6), (2/3, -5e-6), (1, 0)
cross at (0.5, 0). Flatness of the second cubic is 5e-6, past
the 1e-6 chord tolerance, so it is not flat and not straight.
The samples are about ±7.51e-10. The floor drops them. Controls
on the segment report the self-overlap. Controls 1e-5 off it
do too. Removing the floor reports this inflection. The tangent
circles stay no self-overlap: same sign, about 1.7e-6. The hump
at y=2.25 stays none. The figure tests still pass with the
floor removed. Removing the floor does not fix the uneven hump.

The cubic (0, 0), (-1, 0), (2, 0), (1, 0) lies on the x-axis
from about x=-0.207 to x=1.207. The cubic (0.6, -0.4),
(1.4, -0.3), (0.9, 0.2), (1.6, 0.5) crosses it at about
(1.146, 0). No self-overlap. A line at x=1.15 is one. Depth 32
does not find the curve crossing. The segment between the
extreme points does: `_line_cubic_hits` reports (1.146, 0).
The endpoint segment does not contain the point.

The touching circles still meet within 2e-10. The inner center
is subject and is not weed area. That remains
`touching-hole-counter`. `_painted_parts` was not changed.
The surround module, the window, the host, and the guide were
not edited.

Result: three defects remain in the change. The named checks
passed. `pytest tests/test_figures.py` passed (20 passed, not
skipped). Qt loaded. No Inkscape.

`_cubics_change_sides` projects the chord point onto each curve
before it samples. The chord fraction is not the curve parameter.
`_curve_changes_side` treats an opposite sign as a side change and
no longer requires the samples to clear 1e-9. A same-sign touch
stays out. `_cubic_pair_walk` sends a collinear cubic that runs
past its ends through `_line_cubic_hits` on the segment between
the curve's extreme points. The endpoint segment misses that
length. `_painted_parts` was not changed.

The hump (0, 0), (0, 3), (3, 3), (3, 0) and (-1, 2.05),
(1, 2.0501), (2, 2.0499), (4, 2.05) are two self-overlaps near
(0.849, 2.05) and (2.151, 2.05). y=2.25 is none. The radius-10
ellipse and (-12, 1), (-11.5, 1.01), (-11, 0.99), (12, 1) are
two, near (-9.950, 1.001) and (9.951, 0.999). The inflection
(0, -0.125), (1/3, 0.125), (2/3, -0.125), (1, 0.125) and
(0, 0), (1/3, 5e-6), (2/3, -5e-6), (1, 0) are one at (0.5, 0).
The tangent circles stay none. (0, 0), (-1, 0), (2, 0), (1, 0)
and (0.6, -0.4), (1.4, -0.3), (0.9, 0.2), (1.6, 0.5) are one
near (1.146, 0). The ellipse with the triangular hole stays the
counter.

The touching circles still meet within 2e-10. The inner center
is subject and is not weed area. That remains
`touching-hole-counter`. The surround module, the window, the
host, and the guide were not edited.

Checked with `pytest tests/test_figures.py` (23 passed). Qt
loaded. Nothing was skipped. No Inkscape.

Review summary: one defect remains in the change. The named
checks passed. A straight cubic whose controls lie on the
segment between its ends is that segment, and those crossings
are self-overlaps. A touch that stays on one side is not. An
uneven cubic is sampled on the curve, so the hump with controls
1e-4 off y=2.05 is two self-overlaps, and the ellipse crossings
are two. An opposite sign is a side change, so the shallow
inflection is one self-overlap and the tangent circles stay
none. A collinear cubic on the endpoint line is the segment
between its extreme points, and the crossing on that extra
length is a self-overlap. The same extra length is missed when
the controls leave the line. The pass is `cr-04.md`.

Context worth keeping: `_collinear_extent` accepts a bow only
through 1e-9. From a bow of 1.1e-9 through 3e-6 the figure
check reports none. A bow of 4e-6 is found again. The side test
is not called in the gap. The walk has already stopped on a
chord that ends at x=1. The open cubic (0, 0), (-1, 1e-6),
(2, -1e-6), (1, 0) still runs to about x=1.207. It crosses
(0.6, -0.4), (1.4, -0.3), (0.9, 0.2), (1.6, 0.5) near
(1.146, 0). The extreme-point segment meets the other curve
there. A line at x=1.15 does too. A crossing at x=1.5 is past
the curve and stays none. Widening the 1e-9 gate to 1e-6 does
not cover a bow of 2e-6 or 3e-6. Keep splitting while a control
lies past an end. That reports the 1e-6 bow and still leaves
y=2.25 as none. A bow of 1e-4 on that tangent enters the hump
by about 6e-10 and stays a touch.

The touching circles still meet within 2e-10. The inner center
is subject and is not weed area. A radius-3 circle centered 6
units out is the counter: its center is weed area. That remains
`touching-hole-counter`. `_painted_parts` was not changed. The
surround module, the window, the host, and the guide were not
edited.

Result: one defect remains in the change. The named checks
passed. `pytest tests/test_figures.py` passed (23 passed, not
skipped). Qt loaded. No Inkscape.

An endpoint chord stands in for a cubic only when that piece is
within 1e-6 of its curve and both controls project onto the
segment between its ends. A control past an end keeps that piece
splitting, so the extra length gets its own chord and the side
test runs there. The 1e-9 collinear gate is unchanged.
`_painted_parts` was not changed.

The walk had been stopping on the chord from (0, 0) to (1, 0)
once the bow was within 1e-6. That chord ends at x=1 and does
not contain the crossing. The open cubic (0, 0), (-1, 1e-6),
(2, -1e-6), (1, 0) and (0.6, -0.4), (1.4, -0.3), (0.9, 0.2),
(1.6, 0.5) are one self-overlap near (1.146, 0). Bows of 2e-6
and 3e-6 are one there too. Controls on the line stay one. A
cubic through (1.5, 0) is past the curve and is none. The hump
against y=2.25 stays none.

The touching circles still meet within 2e-10. The inner center
is subject and is not weed area. That remains
`touching-hole-counter`. The surround module, the window, the
host, and the guide were not edited.

Checked with `pytest tests/test_figures.py` (23 passed). Qt
loaded. Nothing was skipped. No Inkscape.

Review summary: no defect remains in the change. The named
checks passed. An endpoint chord stands in for a cubic when
that piece is within 1e-6 of its curve and both controls
project onto the segment between its ends. A control past an
end keeps that piece splitting, so the extra length gets its
own chord and the side test runs there. A touch that stays on
one side is not a self-overlap. The pass is `cr-05.md`.

Context worth keeping: for a bow of 1e-6, 2e-6, or 3e-6 the
walk does not stop on the chord from (0, 0) to (1, 0). The
piece that holds the crossing runs past x=1, from about
x=1.125 to x=1.193. Both controls of that piece project onto
its segment. Flatness there is about 1e-8. The stop is near
depth 11, not depth 32. The bowed curve also passes that
place on the way back. The two meetings are about 1e-7 apart,
inside the same-point tolerance, so they are one self-overlap.
The curve ends near x=1.207. A cubic through (1.5, 0) does
not meet it. The hump against y=2.25 stays none. A crossing
of the same bowed cubic near (0.5, 0), between the ends, is
still one self-overlap. The 1e-9 collinear gate was not
widened. The depth-32 stop can still use an endpoint chord
when a control is past an end. These bows did not reach it.

The touching circles still meet within 2e-10. The inner
center is subject and is not weed area. A radius-3 circle
centered 6 units out is the counter: its center is weed area.
That remains `touching-hole-counter`. `_painted_parts` was not
changed. The surround module, the window, the host, and the
guide were not edited.

Result: no defect remains in the change. The named checks
passed. `pytest tests/test_figures.py` passed (23 passed, not
skipped). Qt loaded. No Inkscape.
