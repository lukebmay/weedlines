# Shallow overlap

**Status:** done

## Goal

Confirm the report. If it holds, two figures whose
outlines cross and whose interiors partially intersect
are a separate-figure overlap, even when the intersection
polygon has no area.

## Do

- First confirm the report. The review note is not proof.
- The report: a radius-10 circle and a radius-3 circle, as
  two figures, with centers 12.97 apart along y=x. The
  outlines cross. A point near (7.064, 7.064) lies in both
  fills, and each fill has a point outside the other.
  `intersected().simplified()` in `_overlap_defects` in
  `src/weedlib/figures.py` has no area. The function
  returns before the outline test, so the figure check
  reports no separate-figure overlap. Distance 12.96
  reports one. Distance 13 reports none.
- If it cannot be confirmed, stop. Do not change production
  code. Say that it is not confirmed.
- If it is confirmed, fix it in this task. When the
  outlines cross and each fill contains a point of the
  other, report one separate-figure overlap. The target
  is a point both fills contain. An empty intersection
  polygon does not erase that. Follow
  `agents/architecture/preflight.md`. Do not edit that
  file.
- Add the regression in `tests/test_figures.py` only when
  the report is confirmed. No Inkscape. Skip when Qt cannot
  load.
- Do not edit the surround module, the window, or the host.
- Distance 7 of these circles is nesting. Do not make that
  touch a separate-figure overlap.

## Checks

- The report is confirmed, or it is not confirmed.
- When it is confirmed: distance 12.97 is one
  separate-figure overlap, and the target is a point both
  fills contain. Distance 12.96 stays one. Distance 13
  stays none. Distance 7 stays nesting, not a
  separate-figure overlap.
- One connected region is one separate-figure overlap.
  A radius-10 circle and a rectangle from x=-3 to x=3
  and y=9.99 to y=9.995, rotated 45 degrees about the
  origin, share one region. The figure check reports
  one separate-figure overlap. The segment between the
  two outline crossings lies in both interiors.
- Two connected regions are two separate-figure
  overlaps. A radius-10 circle and a figure with two
  subpaths, a radius-3 circle at (8, 0) and a radius-3
  circle about (9.171, 9.171), report two. One target
  is near (7.712, 0). The other is a point near
  (7.066, 7.066) that both interiors contain.
- A thin curved band that shares one region is one
  separate-figure overlap. The band's inner border is
  radius 9.99 and its outer border is radius 10.05,
  from one radian below the positive x-axis to one
  radian above it, against a radius-10 circle. The
  shorter band, the same radii from -0.2 to 0.2
  radian, is also one. A piece of the intersection
  polygon is not its own region.
- A thin ring that shares one region is one
  separate-figure overlap. The ring's outer border is
  a 64-sided polygon at radius 10.05, and its inner
  border is a 64-sided polygon at radius 9.99, against
  a radius-10 circle. The outlines do not cross. The
  figure check reports one separate-figure overlap.
  The target is a point both interiors contain. The
  radius-10 circle and the radius-3 circle with
  centers 7 apart stay nesting.
- `pytest tests/test_figures.py` passes without Inkscape.

## Note

The report is confirmed. A radius-10 circle and a radius-3
circle, centers 12.97 apart along y=x, cross twice. The point
about (7.066, 7.066) lies in both fills, and each fill has a
point outside the other. `intersected().simplified()` in
`_overlap_defects` is empty, so the function returned before
the outline test and the figure check reported no overlap.
Distance 12.96 reported one. Distance 13 reported none.
Distance 7 is nesting.

An empty intersection polygon no longer ends the check. When
the bounds meet, each nearer pair of outline crossings whose
midpoint lies in both fills is one separate-figure overlap.
The target is that midpoint. A polygon that still has area
uses the same path as before, so a contained touch is still
nesting.

Checked with `pytest tests/test_figures.py`: 26 passed. Qt
loaded. No Inkscape. Distance 12.97 is one overlap and the
target lies in both fills. Distance 12.96 stays one. Distance
13 stays none. Distance 7 stays nesting. The nesting test was
not changed. The surround module, the window, the host, and
the guide were not edited.

The reviewer then writes the summary, the context worth keeping,
and the result.

Review summary: two defects remain in the change. The named
checks passed. A radius-10 circle and a rectangle rotated 45
degrees about the origin share one connected region, and the
figure check reports two separate-figure overlaps. A radius-10
circle and one figure of two radius-3 circles, one centered at
(8, 0) and one 12.97 along y=x, share two connected regions,
and the figure check reports one. The empty intersection
polygon of the second region is dropped because the first
region still has area. Remedy: each connected region of shared
area is one separate-figure overlap, even when the intersection
polygon missed that region. The target is one point in that
region that both interiors contain. A nearer pair of outline
crossings is not a region. Distance 7 stays nesting. The pass
is `cr-01.md`.

Context worth keeping: Distance 12.97 along y=x has an empty
intersection polygon, two outline crossings, and one target
near (7.066, 7.066) in both interiors. Distance 12.96 still
has polygon area and stays one. Distance 13 has no crossing
and stays none. Distance 7 has polygon area, no outline
crossing, and stays nesting. The rectangle before rotation
runs from x=-3 to x=3 and from y=9.99 to y=9.995. After a
45-degree rotation about the origin, a point near
(-9.153, 4.978) lies outside the circle, and the origin lies
outside the rectangle. The two targets, near (-7.112, 7.019)
and (-7.019, 7.112), have the segment between them inside
both interiors. The two-circle figure reports only the target
near (7.712, 0). The point near (7.066, 7.066) is the missed
region: it lies in the outer interior and in the circle near
(9.171, 9.171), not in the circle at (8, 0). The polygon area
there is about 22.59, the kept region only. Two radius-10
circles centered 40 apart, and two radius-3 circles each
12.97 along y=x from one of those centers, are two regions
with an empty polygon and must stay two overlaps, near
(7.066, 7.066) and (47.066, 7.066). The product diff is
`src/weedlib/figures.py` and `tests/test_figures.py`.

Result: Two defects remain in the change. The named checks
passed. No bug outside this change. `pytest tests/test_figures.py`
passed (26 passed). Qt loaded. No Inkscape.

The two counts are fixed. A nearer pair of outline crossings
was one overlap, so the rotated band's four crossings became
two. A region the boolean dropped was ignored when another
region of the same pair still had polygon area, so the
two-circle figure kept only the deep lens.

Polygon components are unchanged. A region the polygon missed
is the crossings joined by a border arc inside the other fill,
or by a chord that lies in both fills. One joined component is
one overlap. The target is the centroid of those crossings when
both fills contain it, otherwise another point of that region
that both contain. A component the polygon already contains is
not reported again. Distance 7 still returns before that, so
nesting is unchanged.

Checked with `pytest tests/test_figures.py`: 29 passed. Qt
loaded. No Inkscape. The rotated band is one overlap and the
target lies in both fills. The two-subpath circles are two
overlaps, one in each circle. Distance 12.97 is one and the
target lies in both fills. Distance 12.96 stays one. Distance
13 stays none. Distance 7 stays nesting. Two empty lenses
40 apart stay two. The surround module, the window, the host,
and the guide were not edited. No bug outside this change.

Review summary: one defect remains in the change. The named
checks passed. A radius-10 circle and a thin curved band share
one region, and the figure check reports that region as
several separate-figure overlaps. The long band, inner radius
9.99 and outer radius 10.05, from one radian below the
positive x-axis to one radian above it, is one region and
eleven overlaps. The shorter band, the same radii, from -0.2
to 0.2 radian, is one region and three overlaps. Remedy: one
connected region is one separate-figure overlap. The target
is one point in that region that both interiors contain. A
piece of the intersection polygon is not its own region. The
pass is `cr-02.md`.

Context worth keeping: Distance 12.97 along y=x stays one
overlap, target near (7.066, 7.066), in both interiors.
Distance 12.96 stays one. Distance 13 stays none. Distance 7
stays nesting. The rotated rectangle, from x=-3 to x=3 and
y=9.99 to y=9.995 before a 45-degree turn about the origin,
stays one overlap, and the target lies in both interiors.
The two-subpath circles stay two overlaps, one in each
circle. Two empty lenses 40 apart stay two. The long band's
outline uses 24 straight pieces on each arc. At radius
9.995 both interiors contain the arc from angle -0.999 to
0.999 with no gap. The eleven targets lie on that arc, from
about (6.429, -7.644) through (9.990, 0) to about
(6.429, 7.644). The origin lies in the circle only. The
point (10.04, 0) lies in the band only. The shorter band's
three targets are near (9.830, -1.799), (9.830, 1.799), and
(9.993, 0). A straight segment between those targets leaves
the band. The product diff is `src/weedlib/figures.py` and
`tests/test_figures.py`.

Result: One defect remains in the change. The named checks
passed. No bug outside this change. `pytest tests/test_figures.py`
passed (29 passed). Qt loaded. No Inkscape.

The curved band was one shared region. The boolean cut it into
pieces, and a straight chord between those pieces leaves the
band, so each piece was its own overlap. Pieces that meet the
same crossing component through both fills are now one overlap.
A boolean point that does not lie in both fills is not an
overlap. The target is one point of that region in both
interiors. Distance 7 still returns before that, so nesting
is unchanged.

Checked with `pytest tests/test_figures.py`: 30 passed. Qt
loaded. No Inkscape. The long band, 24 straight pieces on each
arc from -1 to 1 radian, is one overlap and the target lies in
both fills. The short band, from -0.2 to 0.2 radian, is one.
The rotated band stays one. The two-subpath circles stay two.
Distance 12.97 is one and the target lies in both fills.
Distance 12.96 stays one. Distance 13 stays none. Distance 7
stays nesting. Two empty lenses 40 apart stay two. The surround
module, the window, the host, and the guide were not edited.
No bug outside this change.

Review summary: one defect remains in the change. The named
checks passed. A radius-10 circle and a thin ring share one
region, and the figure check reports 36 separate-figure
overlaps. The ring's outer border is a 64-sided polygon at
radius 10.05, and its inner border is a 64-sided polygon
at radius 9.99. The outlines do not cross. Remedy: one
connected region is one separate-figure overlap. The target
is one point in that region that both interiors contain. A
piece of the intersection polygon is not its own region.
Outlines that do not cross do not split that region. The
pass is `cr-03.md`.

Context worth keeping: Distance 12.97 along y=x stays one
overlap, target near (7.066, 7.066), in both interiors.
Distance 12.96 stays one. Distance 13 stays none. Distance 7
stays nesting. The rotated rectangle stays one overlap, and
the segment between outline crossings of that region lies
in both interiors. The two-subpath circles stay two. Two
empty lenses 40 apart stay two. The long band, 24 straight
pieces on each arc from -1 to 1 radian, stays one overlap.
The short band, from -0.2 to 0.2 radian, stays one. The
ring has no outline crossing. At radius 9.995 both interiors
contain the whole circle, with no gap. The 36 targets lie
on that ring, including about (-9.988, 0.123) and about
(-6.483, 7.598). The straight segment between those targets
leaves the ring. The origin lies in the circle only. The
point (10.04, 0) lies in the ring only. The point
(9.995, 0) lies in both. A 48-sided ring and a 96-sided
ring of the same radii are the same 36. The product diff is
`src/weedlib/figures.py` and `tests/test_figures.py`.

Result: One defect remains in the change. The named checks
passed. No bug outside this change. `pytest tests/test_figures.py`
passed (30 passed). Qt loaded. No Inkscape.

The ring was one shared region. The boolean cut it into pieces,
and the outlines do not cross, so the crossing join never saw
it. A border that lies in the other fill is now that region,
crossings or not. Boolean pieces that meet it through both
fills are the same overlap, and two such borders that meet
are the same overlap. The target is one point of that region
in both interiors. Distance 7 still returns before that, so
nesting is unchanged.

Checked with `pytest tests/test_figures.py`: 31 passed. Qt
loaded. No Inkscape. The 64-sided ring, outer radius 10.05
and inner radius 9.99, is one overlap and the target lies in
both fills. A 48-sided ring and a 96-sided ring of the same
radii are one each. The long band and the short band stay
one. The rotated band stays one. The two-subpath circles stay
two. Distance 12.97 is one and the target lies in both fills.
Distance 12.96 stays one. Distance 13 stays none. Distance 7
stays nesting. Two empty lenses 40 apart stay two. The
surround module, the window, the host, and the guide were not
edited. No bug outside this change.

Review summary: two defects remain in the change. The named
checks passed. A radius-10 circle and a ring share four
regions, and the figure check reports one separate-figure
overlap. The ring's outer border has vertices at (15, 0),
(0, 15), (-15, 0), and (0, -15). The inner border has
vertices at (10, 0), (0, 10), (-10, 0), and (0, -10), and
that border is the hole. The outlines meet at those four
inner vertices and do not cross. A rectangle from (0, 0)
to (30, 4) and a figure of two rectangles, from (-2, 1)
to (8, 3) and from (8.5, 1) to (32.5, 3), share two
regions, and the figure check reports one. Remedy: each
connected region of shared area is one separate-figure
overlap. A border that lies in the other fill is not one
region when the straight segment between consecutive
samples leaves either interior. A straight segment joins
two regions only when the points along it stay in both
interiors. Sixteen probes on a long segment are not enough
when a gap falls between them. The 64-sided ring stays
one. Distance 7 stays nesting. The pass is `cr-04.md`.

Context worth keeping: Distance 12.97 along y=x stays one
overlap, target about (7.066, 7.066), in both interiors.
Distance 12.96 stays one. Distance 13 stays none. Distance
7 stays nesting. Distance 6 stays nesting. The rotated
rectangle stays one overlap. Its outlines cross four
times, and the segment through that region lies in both
interiors. The two-subpath circles stay two, near
(7.066, 7.066) and (7.712, 0). Two shallow circles 40
apart stay two. The long band, 24 straight pieces on each arc
from -1 to 1 radian, stays one. The short band, from -0.2
to 0.2 radian, stays one. The 64-sided ring stays one.
The outlines do not cross. The target is about
(-9.988, 0.123), in both interiors. At radius 9.995 both
interiors contain the whole circle, with no gap. A
48-sided ring and a 96-sided ring of the same radii stay
one each. The four-vertex ring's four regions contain
(6, 6), (6, -6), (-6, 6), and (-6, -6). The straight
segment from (6, 6) to (6, -6) leaves the ring. The
reported target is about (-5.833, -5.833). The other
three pieces of the intersection polygon, near
(5.833, 5.833), (-5.833, 5.833), and (5.833, -5.833),
have no target. The origin lies in the circle only. The
point (12, 0) lies in the ring only. One shared region
of the two rectangles contains (4, 2). The other
contains (19, 2). The gap point (8.2, 2) lies in the
wide rectangle only. The reported target is (4, 2). The point (-1, 2) lies in the two-rectangle
figure only, and so does (31, 2). The product diff is
`src/weedlib/figures.py` and `tests/test_figures.py`.

Result: Two defects remain in the change. The named checks
passed. No bug outside this change. `pytest tests/test_figures.py`
passed (31 passed). Qt loaded. No Inkscape.

The two counts are fixed. A border that lies in the other fill
was one region, so the four lenses of the four-vertex ring were
one overlap. A straight chord joined the gapped rectangles
because sixteen probes stepped over the gap.

A contained border is now one overlap only while a walk along
it stays in both interiors. A pinch the walk cannot cross is
another region. A chord is cut where it meets either border, and
a point on a border is not interior, so a gap between probes
still splits the regions. The thin ring's corner can be walked,
so it stays one. Distance 7 still returns before that, so
nesting is unchanged.

Checked with `pytest tests/test_figures.py`: 33 passed. Qt
loaded. No Inkscape. The four-vertex ring is four overlaps, one
in each lens, and each target lies in both fills. The gapped
rectangles are two, one on each side of the gap. The 64-sided
ring, the 48-sided ring, and the 96-sided ring stay one. The
long band and the short band stay one. The rotated band stays
one. The two-subpath circles stay two. Distance 12.97 is one
and the target lies in both fills. Distance 12.96 stays one.
Distance 13 stays none. Distance 7 stays nesting. Two empty
lenses 40 apart stay two. The surround module, the window, the
host, and the guide were not edited. No bug outside this change.

Review summary: one defect remains in the change. The named
checks passed. The four-vertex ring is four overlaps. The
gapped rectangles are two overlaps as two subpaths. The same
rectangles, joined by a bridge outside the wide rectangle, are
one outline and three shared regions, and the figure check
reports one. A radius-10 circle and one outline with two arms
share two regions, and the figure check reports one. Remedy:
a border arc is one shared run only while a walk along it
stays in both interiors. Where that walk leaves either
interior, the arc is another region. The pass is `cr-05.md`.

Context worth keeping: Distance 12.97 along y=x stays one
overlap, target about (7.066, 7.066), in both interiors.
Distance 12.96 stays one, target about (7.045, 7.045).
Distance 13 stays none. Distance 7 stays nesting. Distance 6
stays nesting. The rotated rectangle stays one overlap,
target about (-7.066, 7.066), in both interiors. The outlines
cross four times. The two-subpath circles stay two, near
(7.066, 7.066) and (7.712, 0). Two shallow circles 40 apart
stay two, near (7.066, 7.066) and (47.066, 7.066). The long
band and the short band stay one. The 64-sided ring stays
one, target about (-9.988, 0.123), and the outlines do not
cross. A 48-sided ring and a 96-sided ring stay one. The
four-vertex ring is four overlaps, near (5.833, 5.833) and
the three sign changes. The outlines do not cross. The
straight segment from (6, 6) to (6, -6) leaves the ring.
The two-subpath rectangles are two overlaps, at (4, 2) and
(19.25, 2). (8.2, 2) lies in the wide rectangle only. One
outline with vertices (-2, 1), (8, 1), (8, 6), (8.5, 6),
(8.5, 1), (32.5, 1), (32.5, 3), (8.5, 3), (8, 3), and
(-2, 3) shares three regions with the wide rectangle: (4, 2),
(19.25, 2), and the bridge cap (8.25, 3.5). The reported
target is (4, 2). The arc from (0, 1) to (8, 4) has midpoint
(7, 1), and the arc from (8.5, 4) to (30, 1) has midpoint
(12.05, 1). The two arms have vertices (2, 14), (2, 0),
(4, 0), (4, 8), (6, 8), (6, 0), (8, 0), and (8, 14). The
crossings are (2, 9.8) and (8, 6). The short-arc midpoint
(5.374, 8.435) lies in both interiors. The polygon points
are about (3.091, 4.968) and (6.953, 3.556). The reported
target is the left one. The product diff is
`src/weedlib/figures.py` and `tests/test_figures.py`.

Result: One defect remains in the change. The named checks
passed. No bug outside this change. `pytest tests/test_figures.py`
passed (33 passed). Qt loaded. No Inkscape.

The bridged rectangles were one outline and three shared
regions, and the figure check reported one. The two-arm
outline shared two regions, and the figure check reported
one. A border arc stayed one run when its midpoint lay in
the other fill, and a walk flipped onto the other side of a
corner. A vertex the outlines only meet did not end the run.

A border arc is now one shared run only while a walk along
it stays in both interiors, on one side of the border, from
one end of the arc to the other. Where that walk leaves
either interior, the arc is another region. A vertex touch
inside the arc is another region too. Crossings are not
joined across that break. Distance 7 still returns before
that, so nesting is unchanged.

Checked with `pytest tests/test_figures.py`: 35 passed. Qt
loaded. No Inkscape. The bridged rectangles are three
overlaps, at (4, 2), (8.25, 3.5), and (19.25, 2), each in
both fills. The two-arm outline is two, near (3.09, 4.968)
and (6.953, 3.555). The long band and the short band stay
one. The rotated band stays one. The 64-sided ring, the
48-sided ring, and the 96-sided ring stay one. The
four-vertex ring is four. The gapped rectangles are two.
The two-subpath circles stay two. Distance 12.97 is one and
the target lies in both fills. Distance 12.96 stays one.
Distance 13 stays none. Distance 7 stays nesting. Two empty
lenses 40 apart stay two. The surround module, the window,
the host, and the guide were not edited. No bug outside
this change.

Review summary: no defects remain. The named checks passed.
The bridged rectangles are three overlaps, at (4, 2),
(8.25, 3.5), and (19.25, 2), each in both interiors. The
two-arm outline is two, near (3.091, 4.968) and
(6.953, 3.556), each in both interiors. The area above the
notch connects to the left arm and is not a third region.
The pass is `cr-06.md`.

Context worth keeping: Distance 12.97 along y=x stays one
overlap, target about (7.066, 7.066), in both interiors.
Distance 12.96 stays one, target about (7.045, 7.045).
Distance 13 stays none. Distance 7 stays nesting. Distance
6 stays nesting. The rotated rectangle stays one overlap,
target about (-7.066, 7.066), in both interiors. The
two-subpath circles stay two, near (7.066, 7.066) and
(7.712, 0). Two shallow circles 40 apart stay two, near
(7.066, 7.066) and (47.066, 7.066). The long band and the
short band stay one. A band from -3 to 3 radians, 64
straight pieces on each arc, stays one. The 64-sided ring
stays one, target about (-9.988, 0.123), and the outlines
do not cross. A 48-sided ring and a 96-sided ring stay one.
The four-vertex ring is four overlaps, near (5.833, 5.833)
and the three sign changes. The outlines do not cross. The
gapped rectangles are two, at (4, 2) and (19.25, 2). The
bridged outline is three, at (4, 2), (8.25, 3.5), and
(19.25, 2). (8.2, 2) lies in the wide rectangle only.
(-1, 2) and (31, 2) lie in the bridged outline only. The
two-arm targets are about (3.091, 4.968) and
(6.953, 3.556). The segment between them leaves the arms:
the midpoint about (5.022, 4.262) lies in the circle only.
(5, 8.5) lies in both and belongs to the left region. The
outlines meet at (6, 8). The product diff is
`src/weedlib/figures.py` and `tests/test_figures.py`.

Result: No defects remain. The named checks passed. No bug
outside this change. `pytest tests/test_figures.py` passed
(35 passed). Qt loaded. No Inkscape.
