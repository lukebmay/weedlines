# Paths

When to use: Anchors, segments, handles, or how a fill rule decides
an interior.

**Owner:** human. Agents may propose edits; apply only with explicit
permission.

The library does not read the Inkscape document. The host passes
path records. [`boundary.md`](./boundary.md) is the conversion and
the units. This part is the path those records already are.

A path is an ordered list of subpaths, not a general graph. One
subpath is a chain, or a loop when closed. An anchor on it meets
at most two segments. An open subpath has two endpoints of one
segment each. A lone moveto meets no segment. A branch is not an
anchor. A control point is not an anchor. Touching subpaths share
a place in the plane. They do not share a vertex a walk can turn
through.

SVG path data stores commands and coordinates. It does not store
a node type. Cusp, smooth, and symmetric are editor constraints
on handles. Inkscape calls the unconstrained anchor a cusp and
also has auto-smooth. Illustrator calls the pair a corner point
and a smooth point, and has no separate symmetric type. A smooth
constraint keeps the two direction lines on one straight line
through the anchor. That is tangent continuity. It is not a
straight coast and it is not curvature continuity. A symmetric
constraint also keeps the direction lines the same length. An
endpoint is not one of these types. It has one direction line
when the incident segment is a curve, and none when that segment
is a line.

A direction line runs from an anchor to a control point.
Illustrator calls that point a direction point. The direction
line is not a cut and not a coast.

A straight segment joins two anchors. A quadratic Bézier has one
control point. A cubic has two. The cubic is B(t) = (1-t)^3 P0
+ 3(1-t)^2 t P1 + 3(1-t) t^2 P2 + t^3 P3, for t from 0 to 1,
from anchor P0 to anchor P3. The derivative at t = 0 is
3(P1 - P0). That direction is the direction line. The parametric
speed is three times the length of that line. Curvature also
uses the second derivative.

One cubic can change the sign of its curvature twice. It can
cusp, where the derivative vanishes, or loop. The point at
t = 1/2 is not the farthest point from the chord. The arc length
has no elementary closed form.

The library's walk sees line segments and Bézier segments. A
quadratic is a Bézier with one control point. An elliptical arc,
after conversion, is not an arc atom.
[`boundary.md`](./boundary.md) is that conversion.

A closepath is a real straight segment, and the subpath is
closed. The straight join a fill paints across an open subpath
is not a closepath. [`preflight.md`](./preflight.md) is that
join.

The fill rule decides the interior. Nonzero winding sends a ray
to infinity and counts +1 or -1 by the direction of the coast.
Zero is outside. Anything else is inside. Even-odd counts
crossings, and an odd count is inside. A figure-8 is one
subpath that crosses itself. Its lobes wind +1 and -1. Both
rules fill both lobes. The crossing is a boundary point.
[`preflight.md`](./preflight.md) names that crossing a
self-overlap.

A counter is another closed subpath whose outline does not
cross the outer outline. Even-odd leaves the inner region
outside. Nonzero leaves it outside only when the windings
cancel. This library classifies interiors with the even-odd
rule. A same-winding inner ring is a hole under that rule.
Nonzero would fill it. [`preflight.md`](./preflight.md) is a
counter, nesting, and a separate-figure overlap.

Union, difference, intersection, and exclusion are editor
operations. They write new path data. SVG has no boolean
command. A hole in the result is a counter. The library
classifies the result. It does not replay the operation.
