# Probes

Open this when the task says the attempt matters. This
note is not the guide. None of these is a named measure.

One old candidate score is reach squared, divided by
reach plus mouth. Mouth and reach were never one
construction. Do not write that score into the guide.

The kinds of number worth probing, as examples only:

- Depth, or the length of the cavern.
- A ratio of that depth to the width of the mouth.
- An angle, as motion past 90 degrees from a starting
  point.
- How quickly the coast becomes concave.

A 90-degree zig-zag is the picture. Large teeth would
need each cave closed. The same teeth, small enough
that the vinyl thickness keeps the waste off the
piece, would not. A probe should show that size
difference as a number. It should stay fast.

## Zig-zag record

`cavern.probe` returns three numbers for each cavern
on one outline. None of these is a named measure.

- Length: the coast through that cavern, from the
  vertex before the first reflex turn through the
  vertex after the last. This is the length kind.
  It is not a depth taken from a mouth.
- Turn: the total right turn along that coast, in
  radians. This is the angle kind.
- Turn per unit length: that turn divided by that
  length. This is how quickly the coast becomes
  concave.

The ratio of depth to the width of the mouth is
skipped. That kind needs a mouth, and this walk does
not define one. Mouth and reach stay two readings.
Neither is crowned. Reach squared over reach plus
mouth is not computed.

Large tooth, in user units. Outline (0, 0), (30, 0),
(30, 20), (18, 20), (18, 8), (12, 8), (12, 20),
(0, 20):

- length 30
- turn pi
- turn per unit length pi/30

The same tooth scaled by 0.01:

- length 0.3
- turn pi
- turn per unit length pi/0.3

Length and turn per unit length change with size.
The turn does not. No number is chosen.

One call on that large tooth, 8 vertices, took
5.98e-6 s. One call on a comb of 200 of the same
tooth, 804 vertices, took 7.09e-4 s. Both are the
mean of repeated calls. The longer walk follows the
outline. The test does not encode a time limit.

## Segment readings

A chord length divided by a curve length is scale-free. On
the recorded straight tooth each edge scores 1, so the tooth
is invisible. The ratio does not separate length 30 from
length 0.3.

The distance from a chord to a cubic, as a length, changes
with size. The parameter midpoint is not the farthest point.
That distance and the chord-to-arc ratio do not convert into
each other, except as a scale-free pair on a circular arc,
which this library does not keep.
[`../../architecture/paths.md`](../../architecture/paths.md)
is that cubic.

An unsigned distance gives the same reading to a convex
corner and a reflex corner. Only the weed side is a cavern.
[`../../architecture/algorithms.md`](../../architecture/algorithms.md)
is that side.

A line has no curve depth. The recorded zig-zag is lines.

None of these is a named measure. Do not write them into
the guide. Mouth and reach stay two readings. Reach squared
over reach plus mouth stays uncomputed.

Growing a contiguous reflex run along one subpath is still
this probe. It is not a conquer cut. The stop, including a
tube's straight walls, a comb, and a cavern in the floor of
a bay, is not known. Do not invent a mouth to hold the stop.

## Size beside shape

None of this is a named measure. Do not write it into
the guide.

The shape reading may be scale-free. Size is a later
threshold beside it. The recorded teeth share a turn
and differ in coast length. The length that can
separate them is the length of the reflex run, the
flap. It is not the length of the closing segment. A
short close across a long slot is a seal you still
want. It is not area. A long thin tube has little area
and a bad peel. It is not one side of the page. A
rotated tube is long and can look short on an axis.
[`../../architecture/algorithms.md`](../../architecture/algorithms.md)
is the size threshold beside the shape.

A one-degree zig-zag is a shallow wave while the flap
stays short. The same angles on a long flap are still
a shallow shape, and the size step is what sees the
flap. A high wave can be tangent-continuous and still
be a deep pocket. A smooth node is tangent continuity,
not a milder cavern. The same anchors with smooth
handles can be the same pocket or a deeper one.
[`../../architecture/paths.md`](../../architecture/paths.md)
is that node.

Closing because the next segment leaves a smoothness
band, then judging the rest on that close, fails the
tube: the walls are straight, so the close falls at
the floor or does not fall at all, and the outer peel
still enters. It fails a comb: one running total can
span many teeth, or a reset can seal a sharp tooth at
either size. It fails a smooth high wave: every small
step stays inside the band. It fails a coarse mild
wave: one sharp sample closes it. The walk reads the
outline. It does not write a possible seal back in as
the next segment.

A circle is not the target. Regularity of the tangent,
convexity, and the isoperimetric quotient meet at a
circle and disagree elsewhere. A stadium is smooth and
not round. A long capsule is convex and not round. A
square is convex and not smooth. Chasing the quotient
cuts convex coast.

A convex hairpin is not a cavern. A cut that rounds
the piece takes the piece apart. A sliver of waste in
a crotch is a length, not a reflex run. The sheet
reduction is
[`../../architecture/algorithms.md`](../../architecture/algorithms.md).
Conquer already
owns a closed loop of waste, and it does not run.

Mouth and reach stay two readings. Reach squared over
reach plus mouth stays uncomputed.

## Segment atomics

None of these is a named measure. Do not write them into
the guide.

The sign is the weed coast. With the weed area to the
left, a left turn is not a cavern and a right turn is
the reflex side. The piece's interior angle is the other
side of that turn. Under 180 degrees on the piece is the
weed's cavern. Over 180 degrees on the piece is the bend
a closing cut must not take apart. Paint is not the side.
Swap moves the weed.

On one piece of a segment that does not change the sign
of its curvature:

- Signed bow. The greatest distance from the chord to
  the curve. The bow is a signed length. A valley on the
  weed side is negative. A ridge on the other side is
  positive. An absolute value drops the side. Zero when
  the piece is straight. Not the point at the middle of
  the parameter.
- Bow over chord. That bow divided by the chord length.
  The scale-free shape of that piece. Zero when the
  piece is straight. A ratio of mouth length to flap
  length is not this reading. Dividing by the bow is
  undefined on a straight piece.
- Tangent turn. The signed turn of the tangent along
  that piece. Scale-free. Zero on a straight piece.
- Anchor turn. The signed turn at an anchor, between
  the two incident tangents. Scale-free. It does not
  see a bow between the anchors. A smooth constraint
  makes it zero, and the coast can still bend.

Total signed turn along one reflex run is the angle
kind already recorded in this note. It is not a new
measure.

An inflection splits a cubic before these readings. One
cubic is not one bow. A cubic has at most two
inflections.

The change from one reading to the next is not the
total turn. On a circular bow that change is zero. The
sum of those changes is the last reading minus the
first. The worst reading in a run is not the run. A
comb is every gap.

A corridor mouth is still not defined. The chord of one
piece is not that mouth. A short bow across a wide
chord is a different shape from the same bow across a
narrow chord. The same shape at two sizes is a different
pair. Neither the length nor the ratio decides. Reach
squared over reach plus mouth stays uncomputed.

A disk of waste in a hole, a ring around a figure, and
a spiral corridor are different peels. No turn count is
chosen. A running total of turn on a surround is not
the cavern walk. The ring and its opening are
[`../../architecture/algorithms.md`](../../architecture/algorithms.md).

## Corridor pictures

None of this is a definition or a measure. Do not write
it into the guide.

On a Y of waste, each leg can look sealable on its own.
One seal at the junction retires the other two. After
the stem is sealed, the two arms are one remaining
corridor. Starting on an arm instead makes that arm the
first lift, and the stem plus the other arm the corridor
that remains. The three seals are alternatives. They are
not three cuts. Recording that dependence is not a walk
that writes a possible seal back into the outline.
[`../../architecture/algorithms.md`](../../architecture/algorithms.md)
is that search.

A widen is not a mouth. Hourglass waves are still one
corridor. Expansion and a fog of nearby coast are two
different notices. Neither is chosen. A connector to a
revealed point is not the next segment of the walk. A
pinch across the piece is not one of these notices.

A corridor may be as long as the pull. A spiral is one
corridor. It is not broken for length, and it is not
broken because a later winding comes near.

A constant width has no single narrowest place. Width
zero is not a funnel. The ring and its opening are
[`../../architecture/algorithms.md`](../../architecture/algorithms.md).

A thin crescent is a strip from horn to horn. A fat
crescent is a patch. The horns are not mouths. A disk
with an interior hole tangent to the outer edge is a
sheet pinched at a point. The hole stays a counter. The
pinch is not a cut and not an overlap. A square is not
a different kind from a short corridor. The sheet
reduction is
[`../../architecture/algorithms.md`](../../architecture/algorithms.md).

These pictures are not one definition of a corridor.
Convexity stays a separate problem. The four segment
readings stay four readings. No formula joins them.

## Handoff

None of this is a measure. Do not write these pictures
into the guide.

Working pictures, each a test a later agent can apply:

- A corridor is simply connected waste whose maximal
  inscribed disks are centered along one arc. The arc
  is the length. The width is the diameter in
  [`../../architecture/algorithms.md`](../../architecture/algorithms.md).
  The two coasts are where the disks touch
  the boundary. With the weed on the left, those coasts
  head opposite ways along the arc. "Roughly the same
  direction" means those headings after one coast is
  reversed. It is not the sign of one coast's turn. A
  stem, a spiral, an hourglass, a thin crescent, and a
  ring after its one opening are this picture. The
  strip may be long.
- Ring, loop, and radial corridor are one thing. The
  opening may be cut.
  [`../../architecture/algorithms.md`](../../architecture/algorithms.md)
  is that rule.
- A spiral is a corridor that encircles itself and
  stays simply connected. A later winding is the same
  strip. Length does not break it.
  Nearness does not break it.
- A funnel is weed open at both ends. Width zero is
  not a funnel.
  [`../../architecture/algorithms.md`](../../architecture/algorithms.md)
  is that rule.
- A square is not a different kind from a short
  corridor.
  [`../../architecture/algorithms.md`](../../architecture/algorithms.md)
  is a sheet.
- A Y is a branch in those centers. The closes are not
  independent. One seal retires the other two.
- An hourglass is one corridor. It is not split only
  because the width changes. If a split is required,
  the place is the neck.

A hole tangent to the outer outline from inside is
still a counter. The outlines meet at a point and do
not cross. A loop around the hole remains. The peel
can start at that point because the width is zero. No
cut is added. The point is not an overlap and not a
retrace. Calling the waste a disk, or calling the loop
gone, is the picture that was rejected.

Fog: a radial neighborhood may notice a convex tip, an
anchor turn that is not a cavern. Connecting one coast
to that tip would split one corridor into two. How far
each new corridor runs is the expensive part. A partial
look may stop. The connector is not the next segment.
Joining a tip because it is convex is the separate
convexity problem. Neither fog nor expansion is chosen.
A widen is still not a mouth.

A partial look at the corridors one seal would leave
is allowed. Walking every leg to the end is the slow
part. A functional peel is enough. Exhaustive subset
search is not required. Travelling-salesman ordering
is not required. A possible seal is not written back
as the next segment.

Convexity stays separate. The four segment readings
stay four readings. No formula joins them.

The next panel is the roles in [`plan.md`](plan.md).
The vector-graphics expert judges path topology and
the overlap rules. The designer judges the peel. The
graph theorist judges structure and efficiency. The
senior developer judges file homes and speed. The
architect writes and
does not implement.
