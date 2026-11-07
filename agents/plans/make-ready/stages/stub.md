# stub

The menu action and the shared check. No auto-correct.
No convert-to-path.

## Library

`src/weedlib/ready.py` owns `build_correction_marks(records)`.
It calls `classify_figures` once and `build_arrow_paths`.
It does not take swap. Swap does not change defects or
the design bounds. It does not write SVG and it does not
read the document.

`arrow_origin(kind, bounds)` is the existing origin helper
in `arrows.py`, used by `build_arrow_paths`. The corner
table is not copied.

The result is the check, the bounds, the arrow paths for
each kind that has a target, and one label per such kind.
The label text is `Dangling ends`, `Figure overlaps`, or
`Self-overlaps`. The color is that kind's arrow color.
The point is the kind origin.

## Host

The effect spawns the child and returns at once. The
child runs the check. It writes the ready file only when
there is a defect. A clear check removes a stale ready
file. `write_correction_svg` is the only correction
writer. It adds one text element at the label point.

`Reimport last ready` places that file with the existing
correction import. `Reimport last weedlines` still places
a weed-line result and refuses a ready file.

The window hint and the correction return name
`Reimport last ready`. They call the same writer.

`Make ready to cut` has no ellipsis. `Auto generate
weedlines…` keeps the ellipsis. The two Reimport names
have no ellipsis. Reimport is one word.

## Not this stage

A single click that inserts the arrows. That holds
Inkscape until the check finishes, because an effect can
change the open document only before the script exits.
The cleanup note records it for the design meeting.
