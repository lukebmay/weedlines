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

The menu is Extensions → Weedlines. The entries are
`Auto generate weedlines…`, `Make ready to cut`,
`Reimport last ready`, and `Reimport last weedlines`.
The ellipsis is only on the first. Reimport is one word.
Inkscape sorts them alphabetically. There is no divider
and no sort prefix.

`Make ready to cut` spawns a child and returns at once.
The effect does not change the open document. The child
runs the check. A defect writes the ready file through
the correction writer. A clear check writes none and
removes a stale ready file. `Reimport last ready` places
that file. `Reimport last weedlines` places a weed-line
result and refuses a ready file.

`Auto generate weedlines…` still opens the detached
window and returns at once. No path geometry aborts and
tells the person to convert objects to paths. Apply writes
`last_result.json` and `last_result.svg`. The ready file
is not that result. The on-screen hint names
`Reimport last ready`. The host does not configure a cutter.

## Result

The window writes one of two results.

A weed-line result is the result the window writes after Apply:
the design copy and the cut paths. Import of that result adds
one layer that holds the design group and the cuts.

Each cut in that result is stroke only. Fill is none. The stroke
is the weed-line color from the window, and the width is 0.25.
The id is `weed-cut-NNNN`. The inline path writes that same
stroke when it adds the layer itself. The preview paints the
same color. The person sets it once.

A correction result has the correction arrows and one text
label for each kind that has an arrow. The label is at that
kind's origin, in the arrow color. The words are "Dangling
ends", "Figure overlaps", and "Self-overlaps". The library's
arrow paths are the path data. The window writes one group per
kind that has at least one arrow, and only those kinds. Each
path id starts with `weedlines-correction`. Shafts have no
fill. Heads use the arrow color. The window does not write a
design copy into this result.

Import of a correction result adds one new layer labeled
"Weedlines corrections" and puts those groups in it. The layer
is above the open document. Import does not add a design copy
and does not delete or rewrite the person's paths.

The correction action does not open a message box. The Apply
notice for a weed-line result stays the notice the window
already shows.
