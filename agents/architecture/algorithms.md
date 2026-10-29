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
helpers in `solvers.py`.

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
from the subject, except for the connector below. A straight
edge of the subject becomes a straight line on the surround,
offset by that distance. A turn on that outline leaves those
lines in their own direction, and its radius is at least the
surround distance, so the turn is no tighter than the
clearance. A circular arc is allowed and is not required. That
outline has no sharp corner, including at an inner corner. A
loop that only follows a hole in the subject is not a surround.

Subject pieces whose gap is less than twice that distance share
one surround. Those pieces are one cluster. Where two surrounds
cross, the library smooths each intersection corner, then draws
one connector between those two points. It does not draw a
separate connector at each crossing. The connector may come
closer to the subject than the surround distance. That is the
overlap exception. The connector meets each smoothed surround
at a hard angle. The angle between the connector and that
surround is from 45 degrees through 135 degrees. The connector
does not blend into the surround.

One length is both the clearance and how tight a turn may be,
so this step has no smoothing control.

The step does not run again inside a cluster. It does not draw
weed lines from the surround to the subject edges.
