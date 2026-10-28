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
user units. The window labels padding, spacing, and collar as
millimetres. The solvers do not convert units.

`weedlib.paths` only splits and joins `QPainterPath` subpaths
for the solvers. Tests and other library callers import
`weedlib` directly. They do not need `inkex`.
