# weedlib

- `__init__.py` re-exports keep fill, the weed solvers, the piece border, surrounds, and SVG path conversion.
- `arrows.py` builds one shaft and one head for each defect target.
- `debug.py` writes the opt-in auto-weed decision log and names the planner phase.
- `keep.py` lists closed subpaths, collapses the one twin, nests them, and builds the keep fill.
- `paths.py` splits and joins painter-path subpaths for the solvers.
- `piece_border.py` builds the two piece-border rectangles around the subject.
- `progress.py` holds the progress, pause, cancel, and focus hooks for a solver run.
- `qt.py` loads the Qt geometry types from enaml, PyQt, or PySide.
- `ready.py` runs the figure check and collects a correction arrow for each kind that has a target.
- `svg_paths.py` converts between an SVG path `d` and a painter path.
