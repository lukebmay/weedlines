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

The aim of every algorithm is that every cavern in a weed
area stays within the allowance the person sets, and that
the algorithm does not make more weed areas than that
requires. A cavern over the allowance becomes its own weed
area. A milder one can remain. The allowance is one length.
It is not the surround distance, the join gap, or either
piece-border length. Those already mean clearance, joining,
and the border. This part does not name how a cavern is
measured. No algorithm uses a measure this part does not
name.

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
the piece size. The person can change that distance. The
outer rectangle starts one eighth of an inch outside the
inner one. The person can change that width on its own.
That strip is the material of the border.
[`boundary.md`](./boundary.md) is both lengths. The window
does not build the rectangles. The outer rectangle is the
only cut outside the inner rectangle. No other weed line
passes outside it.

The library emits the two rectangles together, either before
the other weed lines or after them. It does not split the
pair around those lines. Island-hop remains a mode.

## Surround and Conquer

Surround and Conquer is the mode the window opens on. It uses
the same figure check, the same subject and weed area, and the
same preview colors as the other modes. It does not own those.
Conquer is the next step. It is not specified yet, so the
window leaves its Start disabled and the library does not
emit conquer cuts. This work does not define those cuts.

The first step is the surround. The library builds it from the
subject. The window does not.

The surround distance is a length in document user units. The
window starts it at five percent of the smaller side of the
design bounds, and the person can change it. The window does
not allow a value below zero. Zero is the outer boundary of
the subject. Units stay as [`boundary.md`](./boundary.md)
describes. The other mode knobs do not change the surround.
The inner piece-border distance does, because the clip
uses that rectangle. The border width does not.

The library keeps the surround at least the surround distance
from the subject, except at an end the piece-border clip
leaves on the inner rectangle. A cavern within the allowance
is traced at that distance. A straight edge of a traced
cavern is a straight line at that distance. A cavern over
the allowance is not traced. The surround crosses that
cavern's mouth. It may sit farther from the subject than
the surround distance there, and it does not come closer.
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
piece-border lengths are the border. The cavern allowance
is separate from all of those. None of them stands in for
another. The join gap does not decide which cavern is
traced.

The step does not run again inside a cluster. It does not draw
weed lines from the surround to the subject edges.

The library clips a surround that meets the inner rectangle
to the inside of that rectangle and leaves the surround
open. The cavern test does not close those ends, and it
does not call that gap a cavern. The window does not.
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
