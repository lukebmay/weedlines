# Algorithms

When to use: Frame, grid, island-hop, Surround and Conquer, or a cavern.

**Owner:** human. Agents may propose edits; apply only with explicit
permission.

The library owns the cuts. The window chooses the mode and paints
the weed lines. The figure check is not part of any mode. It runs
first. [`preflight.md`](./preflight.md) is the gate.

## Peel

A weed line exists so the person can peel a weed area off the
backing in one motion. The library cuts the weed area. The
window does not.

A cavern is a concavity in the coastline of a weed area.
Peeled in one direction, a hard cavern turns that coast back
so the peel meets the coast coming the other way. A mild
cavern need not. The picture of a hard cavern is a letter C
peeled from the open side toward the bend. The peel follows
the outer coast until the coast turns into the mouth.
Pulling past that turn tears the vinyl, or the waste lifts
onto the subject. The person has to stop, hold the waste
clear of the subject, and start a second peel inside the
cavern until the two meet. A cavern longer than it is wide
makes that second peel likely to fall onto the subject and
stick. A comb is many of those caverns. A shallow wave is a
mild cavern and often peels in one motion. A bay is this
same concavity. It is not a second coastline object.

The same coastline at a small size can peel cleanly and at a
large size can fall onto the subject. Vinyl has thickness.
A short flap drops less readily than a long one. Absolute
size is part of the difficulty, with the shape.

A scale-free reading of the coast does not carry that
size. Size is its own later threshold, beside the shape
reading. The length it uses is not the length of a
closing segment. This part does not name the threshold.

The aim of every algorithm is that a cavern which would
make the peel fail is sealed by a weed line, and a cavern
which would still peel in one motion is left. Vinyl has
thickness, so the same zig-zag can need a seal on each
tooth when the teeth are large and need none when the
teeth are small.

A convex corner is not a cavern. The weed side of the coast
is the side that can hold one. A bend the other way is the
piece, and a closing cut there takes the piece apart. One
cubic is not one cavern. A coast a measure may score is a
contiguous run of the same reflex sign on one subpath.
Smoothness of a coast is not the editor node type.
[`paths.md`](./paths.md) is that type. This part does not
name that measure.

A measure is a number the library can compute for one
cavern. One cavern may need more than one number. Each
measure this part names has a threshold the person sets.
This part does not name the cavern measures yet. A seal
of one cavern waits on that name. The window offers no
separate cavern threshold until then. The classification
cuts are not that seal. The library may compute candidate
numbers. A
candidate is not a measure this part has named. The
calculation is local to the outline. It may look at
more than one cavern. It does not have to try every
subset, and it does not have to be optimal. It stays
fast enough to run while the person is looking.

A threshold is not the surround distance, the join gap,
or a piece-border length. Those already mean clearance,
joining, and the border. None of them stands in for
another.

## Modes that cut today

Frame, grid, and island-hop are the modes that cut. The window
starts one of them when the preflight gate allows that start.
[`preflight.md`](./preflight.md) is that gate. The keep path for
that run is the subject region. The solvers still call that
region keep, and they still call the weed area waste.

A clear design runs the selected mode the way it does today.
This part does not change cut geometry, clearance, or ranking.
The preview color of a weed line is the weed-line color in
[`preview.md`](./preview.md). The result file uses that same
color. [`host.md`](./host.md) is the stroke.

The window opens on Surround and Conquer. Island-hop is not the
default, and it does not become the default until its pictures
are accepted. `auto` is a deprecated alias of island-hop. An
unknown mode runs as frame. `region` is grid. Island-hop needs
pyclipper. Frame and grid do not. The host names Surround and
Conquer in the job when the person has not chosen a mode.

An open stroke is not a keep interior. It fails the figure
check, so it never reaches a solver from the window.

Frame is a padded box around the keep bounds. Grid is an
axis-aligned hatch over the weed area, plus a closed outline
on the padded work rect. Island-hop peels a frame, then ranked
seals. Hosts call `generate_weeds`. They do not call private
helpers in the solvers package.

The window has one padding number and copies it to all four
sides, plus grid spacing, the island-hop collar, and the output
layer name. A blank layer name is `Weed lines`. The form shows
a knob only in the mode that uses it. [`preview.md`](./preview.md)
is that list. Other knobs stay at solver defaults. Units are
in [`boundary.md`](./boundary.md).

## Piece border

The piece is the subject. The piece size is the axis-aligned
rectangle of that subject. Its sides run with the axes. Its
width is maxX minus minX of the subject. Its height is maxY
minus minY of the subject. The page is not the piece. The
piece size is not the design bounds when a figure lies
outside the subject. [`preview.md`](./preview.md) names those
bounds.

The usual piece border is two rectangles around the piece
size. When there is no outer rectangle, that one rectangle
is the border rectangle.
The inner rectangle starts one eighth of an inch outside
the piece size. That gap is border padding. The outer
rectangle starts one eighth of an inch outside the inner
one. That strip is the border width, and it is the
material of the border. The person can change each length
on its own. [`boundary.md`](./boundary.md) is both
lengths, and the corner radius. The window does not build
the rectangles. The outer border is the only cut outside
the inner border. No other weed line passes outside it.

Border padding is not the padding of frame, grid, or
island-hop. Those modes keep their own padding control.

With rounded corners off, both rectangles have square
corners. With rounded corners on, the library rounds
every corner of both rectangles by the border corner
radius. The radius starts at one quarter of an inch.
Zero is a square corner. The radius is at most half the
shorter side of the inner rectangle, so the corner arcs
do not cross and the strip stays an even width. The
window does not allow a value outside that range. The
radius applies only while rounded corners are on. The
window keeps the number while it is open.

The library emits the two rectangles together, either before
the other weed lines or after them. It does not split the
pair around those lines. Island-hop remains a mode.

## Classification

Classification uses the path atomics in
[`paths.md`](./paths.md). Those atomics are a line, a
cubic, an inflection as a parameter split, and an
anchor turn. Classification does not insert an anchor
into the path.

The border rectangle is the inner rectangle of the
piece border. When the piece border is one rectangle,
that rectangle is the border rectangle. The padding
rectangle is the piece size. It lies inside the border
rectangle. The gap between them is the border padding
already named. It is not a new length.

A positive figure is a figure whose interior is
subject. A negative figure is a figure whose interior
is weed. Figure keeps the meaning in
[`preflight.md`](./preflight.md). Padding is weed area
for both. On a negative figure the library cuts the
padding rectangle, so the piece is not left attached
to the padding. On a positive figure the library does
not cut the padding rectangle. That padding is already
beside other weed. The combined weed is still broken
into weedable chunks.

Ring, loop, and radial corridor are the weed around
one figure. They are one thing. A corridor that only
joins two figures is not a ring. One opening turns
the ring into a corridor. The library may cut that
opening. The opening is not a second class.

The width of waste at a place is the diameter of the
largest circle that fits in the waste there. A sheet
is waste where that circle is wider than the sheet
threshold. The threshold is adjustable and starts at
8 inches. It is that diameter. It is not a radius.
That inch is the kind of length
[`boundary.md`](./boundary.md) already describes. A
long thin corridor is not a sheet. A square and a
short rectangle are corridors of the same kind. They
are sheets only when that circle is over the
threshold. Area along a corridor does not make a
sheet. A rotated thin corridor stays a corridor.

The sheet reduction strokes every border of the sheet
at a width equal to the sheet threshold and converts
that stroke to a path. The stroke is centered on the
border, so half the threshold lies inside the sheet.
That half is the radius of the circle whose diameter
is the threshold. The part of the stroke inside the
sheet is the band beside the border. The sheet remote
is the sheet with that band removed. Intersecting the
band with the sheet again leaves the band. If no
remote remains, the waste is not a sheet. The remote
begins half the sheet threshold in from the border.
A point lies in the remote only when it is farther
than that half from every border.

The library then surrounds the remote. That surround
is an internal surround at the surround distance
already named. The corridor to solve is the weed
between the sheet border and that surround. Its inner
coast is the surround. The next test is the interior
of the surround, not the raw remote. The outer coast
of that interior is the surround. The reduction
repeats while that interior is a sheet. When the
remote is several pieces, pieces whose gap is less
than twice the surround distance share one surround,
the cluster rule already named.

The smoothness threshold is a person-set option on a
coast. This part does not name its formula. It is not
an editor node type and not a turn at one anchor.
[`paths.md`](./paths.md) is that type. A coast may be
a corridor coast inside that threshold. It need not
be one arc. A small 90-degree zigzag can sit inside
it.

Two figures join by one cut when the coast of the
composite stays within the smoothness threshold, and
by a corridor of two cuts otherwise. The corridor is
an extra weed area. Either join is enough. The join
makes one composite. A composite is the figures or
composites being joined, together with the join
medium. The medium is that one cut or that two-cut
corridor. The cut adds no area. The corridor adds its
area. A composite is not a figure, not a path
element, and not an editor union. Figure keeps the
meaning in [`preflight.md`](./preflight.md). During
the reduction the composite is the unit that can be
joined again. The library links the closest open gap
first and repeats. The gap is measured through open
weed. A link does not cross a figure or an earlier
link. On a tie, one link is enough. A link corridor
may be wider than the sheet threshold. After that
corridor exists, it is reduced as a sheet.

The weed outside one smooth figure is a corridor when
its coast meets the smoothness threshold. A
right-angle corner on that ring may lie inside the
threshold. This part does not name that limit. The
library may smooth a rough corridor. A smoothness cut
joins convex point to convex point, stays in the
weed, and may be a curve or more than one segment.

A spur is trimmed only when the fitting circle along
it is wider than the sheet threshold. The trim cuts off
the part past that circle. A piece that fits inside a
circle of the sheet tolerance, including a trimmed tip,
is left or joined to the neighboring weed. It counts as solved. Joining it may
leave that weed slightly over the sheet threshold. The
sheet tolerance is adjustable and starts at 1 inch. That
inch is the kind of length
[`boundary.md`](./boundary.md) already describes. It
is not the sheet threshold.

The piece border is the outermost surround, whether
or not an outer rectangle gives the border thickness.
An internal surround may recurse around a cluster
inside that border. It does not wrap the border. This
part does not name a new surround distance. It does
not use an average gap. Conquer is the joins, the
opening of a ring, the sheet reduction, and the
smoothing. An internal surround is not required
first.

A funnel is weed open at both ends. Waste that closes
to width zero is a bucket. A cave is that bucket. A
bucket is not a funnel.

## Surround and Conquer

Surround and Conquer is the mode the window opens on. It uses
the same figure check, the same subject and weed area, and the
same preview colors as the other modes. It does not own those.
It is one run. The classification above is the mapping.
A cut is not written back as the next segment of the
outline. When a seal exists, the outer peel follows the
seal, and the weed inside it is a different coast.

The library builds the internal surround from the
subject. The window does not. That internal surround
uses the surround distance below.

The surround distance is a length in document user units. The
window starts it at five percent of the smaller side of the
design bounds, and the person can change it. The window does
not allow a value below zero. Zero is the outer boundary of
the subject. Units stay as [`boundary.md`](./boundary.md)
describes. The other mode knobs do not change the surround.
Border padding does, because the clip uses the inner
border. The corner radius does too, when rounded
corners are on, because the clip follows those corners.
The border width does not.

The library keeps the surround at least the surround distance
from the subject, except at an end the piece-border clip
leaves on the inner border. Once this part names the
smoothness formula, a cavern within that threshold is
traced at that distance. A straight edge of a traced
cavern is a straight line at that distance. A cavern
over that threshold is not traced. The surround crosses
that cavern's mouth. It may sit farther from the
subject than the surround distance there, and it does
not come closer. This part does not name that formula,
so the internal surround does not apply this test and
does not bridge a cavern from a candidate number.

That bridge has no sharp corner. The weed area inside the
bridged cavern is not part of the outer peel. This step
does not cut that cavern up. A turn is no tighter than the
surround distance. A circular arc is allowed and is not
required. The outline has no sharp corner, including at an
inner corner. A loop that only follows a hole in the
subject is not a surround, and the surround does not bridge
that loop. The step emits nothing when the subject has no
area, or when discarding those hole-only loops leaves no
outline. It does not search the weed area for
a substitute. Swap is what makes a region the subject. A region
that swap made the subject can be surrounded.

Subject pieces whose gap is less than twice that distance share
one surround. Those pieces are one cluster. The library unions
every surround that overlaps, then smooths that whole outline.
The outline is as smooth as the clearance allows, and it does
not come closer to the subject than the surround distance.

The join gap is a length in document user units. The window
supplies it. [`boundary.md`](./boundary.md) is the baseline.
Zero joins only surrounds that meet or overlap. Surrounds that
do not meet, but whose separation is at most the join gap, are
unioned and smoothed as if they overlapped. Close cut lines
waste a pass and can lift the vinyl or mark the backing.

The surround distance is the clearance. The join gap
joins surrounds. The two piece-border lengths and the
corner radius are the border. A cavern threshold is
separate from all of those. None of them stands in for
another. The join gap does not decide which cavern is
traced.

The internal surround does not run again inside a cluster.

The library clips a surround that meets the inner border
to the inside of that border and leaves the surround
open. When rounded corners are on, the clip follows the
rounded inner border. The cavern test does not close
those ends, and it does not call that gap a cavern. The
window does not.
The clip keeps the surround off the outer edges of the
subject, so the cutter does not trace those edges again. Four equal squares set in a
rectangle are why: their outer sides must not be the
surround as well. The clip does not cut the subject. The
open ends may sit closer than the surround distance. The
rest of the run stays at least that distance from the
subject. The library does not draw the inner-rectangle
segment between those ends. That segment is part of the
one inner-rectangle cut, and it is the side that closes
the run. A surround that meets the rectangle in more than
one run follows the same rule for each run. A surround
that stays inside the rectangle stays closed. A surround
the clip removes entirely is not emitted.
