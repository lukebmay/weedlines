# Boundary

When to use: SVG path conversion, the Qt binding, or units.

**Owner:** human. Agents may propose edits; apply only with explicit
permission.

The library owns this edge. The host converts at the boundary.
A solver does not read SVG text, and it does not pick a Qt binding.

`weedlib.svg_paths` converts an SVG `d` and a `QPainterPath`.
`weed_path_to_open_d_list` is the open-cut list the extension
writes. `A` and `a` arcs become a line to the endpoint. A host
that needs a true arc converts it before this step.

`weedlib.qt` loads one binding, in this order: `enaml.qt`,
PyQt5, PySide2, PyQt6, PySide6. Coordinates stay in the caller's
user units. The solvers do not convert units.

The window shows every length in one display unit. The job
carries Inkscape's display unit and the scale of one user
unit. The display unit starts as that Inkscape unit. When
the document does not name one, the window uses px. A
dropdown switches the display to another absolute length
from Inkscape's display-unit list. Switching converts the
numbers on screen. Percent and em are not on that list. The
library still receives document user units.

A length this guide names in inches, including the join gap
baseline of a quarter inch, is that real length in user
units under the document scale. It is not a fixed count of
6.35. Padding, grid spacing, and the island-hop collar keep
the solver's user-unit counts. The window shows those counts
in the display unit. It does not relabel the digits.

`weedlib.paths` only splits and joins `QPainterPath` subpaths
for the solvers. Tests and other library callers import
`weedlib` directly. They do not need `inkex`.
