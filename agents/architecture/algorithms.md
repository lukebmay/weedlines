# Algorithms

When to use: Frame, grid, island-hop, or Surround and Conquer.

**Owner:** human. Agents may propose edits; apply only with explicit
permission.

The library owns the cuts. The window chooses the mode and paints
the weed lines. The figure check is not part of any mode. It runs
first. [`preflight.md`](./preflight.md) is the gate.

## Modes that cut today

Frame, grid, and island-hop stay the three runnable modes. The
window starts one of them only when the latest figure check
reports no defect. The keep path for that run is the subject
region. The solvers still call that region keep, and they still
call the weed area waste.

A clear design runs the selected mode the way it does today.
This part does not change cut geometry, clearance, or ranking.
The preview color of a weed line is the weed-line color in
[`preview.md`](./preview.md). The result file uses that same
color. [`host.md`](./host.md) is the stroke.

Frame is the default. Island-hop is not the default, and it
does not become the default until its pictures are accepted.
`auto` is a deprecated alias of island-hop. An unknown mode
runs as frame. `region` is grid. Island-hop needs pyclipper.
Frame and grid do not.

An open stroke is not a keep interior. It fails the figure
check, so it never reaches a solver from the window.

Frame is a padded box around the keep bounds. Grid is an
axis-aligned hatch over the weed area, plus a closed surround
on the padded work rect. Island-hop peels a frame, then ranked
seals. Hosts call `generate_weeds`. They do not call private
helpers in `solvers.py`.

The window shows one padding number and copies it to all four
sides, plus grid spacing, the island-hop collar, and the output
layer name. A blank layer name is `Weed lines`. Other knobs stay
at solver defaults. Units are in [`boundary.md`](./boundary.md).

## Surround and Conquer

Surround and Conquer is a weed-line algorithm. It will have its
own subroutines and parameters. The human has not named those
subroutines or parameters. The window does not list it as a mode,
and the library does not emit cuts for it, until that
specification exists.

When it exists, it will use the same figure check, the same
subject and weed area, and the same preview and import path as
the other modes. It does not own those.
