# Algorithms

When to use: Frame, grid, island-hop, or Surround and Conquer.

**Owner:** human. Agents may propose edits; apply only with explicit
permission.

The library owns the cuts. The window chooses the mode and paints
the weed lines. The figure check is not part of any mode. It runs
first. [`preflight.md`](./preflight.md) is the gate.

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

The window shows one padding number and copies it to all four
sides, plus grid spacing, the island-hop collar, and the output
layer name. A blank layer name is `Weed lines`. Other knobs stay
at solver defaults. Units are in [`boundary.md`](./boundary.md).

## Surround and Conquer

Surround and Conquer is the mode the window opens on. It uses
the same figure check, the same subject and weed area, and the
same preview colors as the other modes. It does not own those.
Conquer is not part of this mode yet. The window does not run
it, and the library does not emit conquer cuts.

The first step is the surround. The library builds it from the
subject. The window does not.

The surround distance is a length in document user units. The
window starts it at five percent of the smaller side of the
design bounds, and the person can change it. The window does
not allow a value below zero. Zero is the outer boundary of
the subject. Units stay as [`boundary.md`](./boundary.md)
describes. The other mode knobs do not change the surround.

The library keeps the surround at least the surround distance
from the subject. A straight edge of the subject becomes a
straight line on the surround, offset by that distance. A turn
is no tighter than the surround distance. A circular arc is
allowed and is not required. The outline has no sharp corner,
including at an inner corner. A loop that only follows a hole
in the subject is not a surround.

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
clearance. The join gap is the only other length.

The step does not run again inside a cluster. It does not draw
weed lines from the surround to the subject edges.
