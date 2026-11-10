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
mild cavern and often peels in one motion.

The same coastline at a small size can peel cleanly and at a
large size can fall onto the subject. Vinyl has thickness.
A short flap drops less readily than a long one. Absolute
size is part of the difficulty, with the shape.

The aim of every algorithm is that a cavern which would
make the peel fail is sealed by a weed line, and a cavern
which would still peel in one motion is left. Vinyl has
thickness, so the same zig-zag can need a seal on each
tooth when the teeth are large and need none when the
teeth are small.

A measure is a number the library can compute for one
cavern. One cavern may need more than one number. Each
measure this part names has a threshold the person sets.
This part does not name the measures yet. No cutting
algorithm seals a cavern, and the window offers no cavern
threshold, until this part names the measure and the
threshold. The library may compute candidate numbers. A
candidate is not a measure this part has named. The
calculation is local to the outline. It does not search
over sets of caverns. It stays fast enough to run while
the person is looking.

A threshold is not the surround distance, the join gap,
or a piece-border length. Those already mean clearance,
joining, and the border. None of them stands in for
another.

## Modes that cut today

Frame, grid, and island-hop are the modes that cut. The window
starts one of them only when the latest figure check reports no
defect. The keep path for that run is the subject region. The
solvers still call that region keep, and they still call the
weed area waste.

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

The piece border is two rectangles around the piece size.
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

## Surround and Conquer

Surround and Conquer is the mode the window opens on. It uses
the same figure check, the same subject and weed area, and the
same preview colors as the other modes. It does not own those.
Conquer is the next step. It closes each cavern that is
over a named threshold with a weed line, and it cuts
every closed loop of weed material so that waste peels
in one pull. It does not run, and the library emits no
conquer cuts, until this part names the cavern measures
and their thresholds. The window leaves Conquer's Start
disabled until then. Conquer does not change the
surround step.

The first step is the surround. The library builds it from the
subject. The window does not.

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
leaves on the inner border. Once this part names a
cavern measure and its threshold, a cavern within every
named threshold is traced at that distance. A straight
edge of a traced cavern is a straight line at that
distance. A cavern over a named threshold is not traced.
The surround crosses that cavern's mouth. It may sit
farther from the subject than the surround distance
there, and it does not come closer. Until a measure and
its threshold are named, the surround does not apply
this test and does not bridge a cavern from a candidate
number.

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

There is no smoothing control. The surround distance is the
clearance. The join gap joins surrounds. The two
piece-border lengths and the corner radius are the
border. A cavern threshold is separate from all of
those. None of them stands in for another. The join
gap does not decide which cavern is traced.

The step does not run again inside a cluster. It does not draw
weed lines from the surround to the subject edges.

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
