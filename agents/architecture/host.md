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
The detached window stays the way a run opens. The host still
returns at once so Inkscape stays usable. The inline path
remains available for the same window.

## Result

The window writes one of two results.

A weed-line result is the result the window writes today after
Apply: the design copy and the cut paths. Import of that result
is unchanged. It adds one layer that holds the design group and
the cuts.

A correction result holds only correction arrows. The library's
arrow paths are the path data. The window writes one group per
kind that has at least one arrow, and only those kinds. The
group labels are "Dangling ends", "Figure overlaps", and
"Self-overlaps". Each path id starts with
`weedlines-correction`. Shafts have no fill. Heads use the arrow
color. The window does not write a design copy into this result.

Import of a correction result adds one new layer labeled
"Weedlines corrections" and puts those groups in it. The layer
is above the open document. Import does not add a design copy
and does not delete or rewrite the person's paths.

The correction action does not open a message box. The Apply
notice for a weed-line result stays the notice the window
already shows.
