# Preflight

When to use: Figures, dangling ends, overlap, or the gate in front
of every algorithm.

**Owner:** human. Agents may propose edits; apply only with explicit
permission.

The library owns this part. The window asks for the result. The
host does not classify figures. The solvers do not run their own
copy of this check.

## What the library reads

The host passes one record per path element, already in document
user units, with that element's transform applied. A record has
the path data, whether each subpath is closed, the computed fill,
and the element id. The library does not read the Inkscape
document.

The library skips an element that belongs to a Weedlines
corrections group. A later run must not treat correction arrows
as design.

A subpath is closed when its path data contains a closepath
command, or its start and end are the same point. Any other
subpath is open. The library does not add a closepath to make an
open subpath closed.

## Figures

A figure is one border taken from one path element. A group is
not a figure. Text that is not a path is not a figure. The host's
existing empty-path abort stays the host's job.

Twins are one figure. A twin is another copy of the same outline.
The library collapses twins with the same near-duplicate collapse
it already uses for keep fill. The extra copy is not a second
figure and is not a defect.

An enclosed figure is a figure whose every subpath is closed.
An unenclosed figure is a figure with at least one open subpath.
Each endpoint of an open subpath that does not meet another
endpoint of that same figure is a dangling end. A closed letter
with a closed hole has no dangling end. An open hole does.

Inkscape paints an open subpath as if a segment joined its two
ends. That segment is not part of the path. The figure check
still uses that painted interior for subject, weed area, and
overlap. It does not use that segment as a real border, and it
does not remove the dangling ends.

## Three defects

The library reports all three. It does not stop at the first.

A dangling end is a defect. The target is that endpoint.

A separate-figure overlap is a defect. It is two figures whose
interiors share area, where each interior also has a point the
other does not. It is also two figures, not nesting, that share
a coincident piece of boundary of positive length, whether or
not the interiors share area. A proper subsegment counts. A
point does not. The painted join is not a piece of boundary.
Each connected region of shared area is one overlap, and its
arrow target is a point inside that region. Each connected
coincident piece is one overlap, and its arrow target is a
point of that piece.

Nesting is not a separate-figure overlap. Nesting means every
point of one interior lies inside the other and the outlines do
not cross. A coincident piece of boundary does not make
nesting an overlap. A letter sitting inside a border is
nesting. Nesting is how a border surrounds other figures. Swap chooses which of
those interiors is the subject. The figure check does not ask
the person to remove the border.

A point touch is not an overlap. A tangent contact that stays on one
side is not a crossing. A tangent contact that changes sides
is a crossing. A shared endpoint is a point touch.

A self-overlap is a defect. It is one figure whose outline
crosses itself. It is also one figure that retraces a
coincident piece of its own boundary of positive length.
Each crossing point is a target. The target of a retrace is
a point of that piece. Two subpaths of the same element that
cross are a self-overlap of that one figure. Two subpaths of
the same element that coincide for a positive length are a
self-overlap of that one figure. A retrace is not a
separate-figure overlap. A closed hole whose outline does not
cross the outer outline is not a self-overlap. That hole is
the counter of the figure.

Overlap does not depend on which region is the subject. Swap
does not add or remove these defects.

## Gate

The window may start an algorithm when the latest figure
check reports no defect. It may also start when every
remaining defect is a self-overlap that is a crossing and
the person has accepted it. The person may accept a
self-overlap that is a crossing. A retrace is a
self-overlap the person may not accept. Accepting does not
change the path, does not remove a dangling end, and does
not make the crossing one peel. A self-overlap stays
reported. The window has no control that starts past a
dangling end, a separate-figure overlap, or a retrace.
This gate is in front of frame, grid, island-hop, and any
later algorithm, including Surround and Conquer.

Make ready may propose a fix for a defect the check reports.
[`host.md`](./host.md) is the approval and what each fix does.
The check itself does not change the path.

The check does not change how a solver cuts a keep path it is
given. A design the gate blocks never reaches the solver
from the window.
