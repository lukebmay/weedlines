# Host

When to use: The Inkscape job, the result file, or import.

**Owner:** human. Agents may propose edits; apply only with explicit
permission.

The host owns the document and the files. The window owns the
decision to write a result. The library owns the arrow paths and
the weed lines.

## Job

The host writes one record per path element in the selection, or
in the whole document when the selection is empty. Coordinates
are document user units with that element's transform already
applied.

The host does not add a closepath. An added closepath would
erase a dangling end before the library can see it. The host
does not union the records into one path before the window runs
the figure check.

Each record includes the computed fill. The host resolves style,
presentation attributes, and inheritance. It records paint as
none, a solid color, or other paint. Opacity of zero is none.

The host omits elements that sit in a group labeled "Weedlines
corrections", and elements whose id starts with
`weedlines-correction`. Those are arrows from an earlier import.

The job still carries the document width, height, and viewBox.
It also carries the display unit and the scale of one user
unit. [`boundary.md`](./boundary.md) is how the window shows
lengths.
The detached window stays the way a run opens. The host still
returns at once so Inkscape stays usable. The inline path
remains available for the same window.

The menu is Extensions → Weedlines. Inkscape sorts the
entries by name. The number is part of each name, and
none of the names end in an ellipsis. The entries are
`1 Auto generate weedlines`, `2 Make ready to cut`,
`3 Reimport last weedlines`, and `4 Reimport last ready cut`.
There is no divider.

`2 Make ready to cut` spawns a child and returns at once.
The effect does not change the open document. The child
runs the check. A clear check writes none and removes a
stale ready file, and it does not open the window. A
defect writes the ready file through the correction
writer, and it opens the detached window on the proposed
fixes. `4 Reimport last ready cut` places that file.
`3 Reimport last weedlines` places a weed-line result
and refuses a ready file.

The window shows each proposed fix before it is kept.
The person approves that fix, approves every remaining
fix, or declines it. A decline keeps the problem in the
piece, and the arrow for it stays. An approval is the
library's replacement paths, shown against the original.
The effect still does not edit the open document. An
approved set is one group, labeled "Ready fixes", in the
ready file. Reimport places that group on the corrections
layer and does not delete the original paths.

The library proposes the path. The window does not invent
one. Stacked nodes that make a self-overlap on a smooth
span: add two nodes on each side of the stack, delete the
stacked nodes, and smooth that span so it stays close to
the original line. Stacked nodes on a corner: add a node
on each side, delete the stacked nodes, and add one
corner node so the angles follow the original path. A
larger self-overlap can be kept with no fix. A figure 8
is a self-overlap the person may want. Figures that
overlap are welded into one path by the same union
Inkscape uses when it unions and combines. A dangling
end is closed by joining the two open ends of that
figure.

`1 Auto generate weedlines` still opens the detached
window and returns at once. No path geometry aborts and
tells the person to convert objects to paths. Apply writes
`last_result.json` and `last_result.svg`. The ready file
is not that result. The on-screen hint names
`3 Reimport last weedlines` for cuts and
`4 Reimport last ready cut` for arrows. The host does not
configure a cutter.

## Result

The window writes one of two results.

A weed-line result is the result the window writes after
Apply. The default contents are the piece border and the
weed lines. The checkbox **Include original design** is
off until the person turns it on. While it is on, the
result also includes the path records the job already
carried. One path per record, in that order, `d` copied
as stored. No closepath is added. A record whose id
starts with `weedlines-correction` is omitted, and a
Weedlines corrections group is omitted. The figure check
still reads the job records, not this result.

Import of that result adds one layer. Inside it, one
group labeled "Weedlines" holds the groups that were
included. The border is one group, labeled "Border".
The weed lines are one group, labeled "Weed lines".
The original design, when included, is one group,
labeled "Original design".

Each cut in that result is stroke only. Fill is none. The stroke
is the weed-line color from the window, and the width is 0.25.
The id is `weed-cut-NNNN`. The border paths use that same
stroke. The inline path writes that same
stroke when it adds the layer itself. The preview paints the
same color. The person sets it once.

A correction result has the correction arrows and one text
label for each kind that has an arrow. The label is at that
kind's origin, in the arrow color. The words are "Dangling
ends", "Figure overlaps", and "Self-overlaps". The library's
arrow paths are the path data. The window writes one group per
kind that has at least one arrow, and only those kinds. Each
path id starts with `weedlines-correction`. Shafts have no
fill. Heads use the arrow color. The window does not write a border, a weed line, or the
original design into this result.

Import of a correction result adds one new layer labeled
"Weedlines corrections" and puts those groups in it. The layer
is above the open document. Import does not add the original
design and does not delete the person's paths. An approved
Ready fixes group, when the ready file has one, is placed
with the arrows. It does not replace the open paths.

The correction action does not open a message box. The Apply
notice for a weed-line result stays the notice the window
already shows.
