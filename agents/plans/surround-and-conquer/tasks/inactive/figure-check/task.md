# Figure check

**Status:** done

## Goal

The library classifies one figure per path record, collapses twins,
and reports dangling ends. It does not read Inkscape, and it does
not close an open subpath.

## Do

- Add `src/weedlib/figures.py` with `classify_figures(records)`.
- A record has path data (`d` or a `QPainterPath`), one closed flag
  per subpath, computed fill (`none`, a solid color, or other
  paint), and the element id. Parse `d` with the existing SVG path
  helper. Do not add a closepath.
- One figure is one path element. Collapse twins by calling the
  near-duplicate collapse keep fill already uses. Do not reimplement
  it. Do not edit `src/weedlib/solvers.py`.
- Each dangling end is a defect whose target is that endpoint.
  Skip a record whose id starts with `weedlines-correction`.
- The rules are `agents/architecture/preflight.md`. This task does
  not build overlap, subject, weed area, or arrows.
- Tests go in `tests/test_figures.py`. No Inkscape. Skip when Qt
  cannot load.

## Checks

- An open subpath is still open. A closed flag does not make the
  library insert a closepath.
- A second copy of the same outline is not a second figure and is
  not a defect.
- A closed letter with a closed hole has no dangling end. An open
  hole does.
- A `weedlines-correction` id is not a figure.
- `pytest tests/test_figures.py` passes. `src/weedlib/solvers.py`
  has no cut change.

## Note

`src/weedlib/figures.py` adds `classify_figures`. Each path record is
one figure. `d` is parsed with `svg_d_to_qpainterpath`, and a closed
flag never adds a closepath, so an open subpath stays open. Twins are
dropped by calling `_dedupe_closed_subpaths`, the near-duplicate
collapse keep fill already uses, rather than a second comparison. A
free endpoint of an open subpath is a dangling defect aimed at that
point. An id starting with `weedlines-correction` is skipped. Overlap,
subject, weed area, and arrows are not in this change.
`src/weedlib/solvers.py` is unchanged.

Checked with `pytest tests/test_figures.py` (4 passed) and an empty
diff of `src/weedlib/solvers.py`.

Review summary: the change matches the task. One figure per path
record, closed twins collapsed by `_dedupe_closed_subpaths`, and a
dangling defect at each free endpoint. A closed flag does not add
a closepath. Correction ids are skipped. Overlap is not in this
change.

Context worth keeping: `classify_figures` returns `FigureCheck`
(`figures`, `defects`). `Figure` is `id`, `path`, `fill`. `Defect`
is `kind` (`dangling`) and `target` (`QPointF`). Closed flags are
not read; a subpath is closed when its ends meet, including a
closepath. Endpoint joints on the same figure are not dangling.
The first closed copy is the one kept, across records and inside
one element. Open copies are not twins, because the keep-fill
helper only dedupes closed subpaths. `_is_new_outline` depends on
that helper returning the same path object.

Result: no defects remain. `pytest tests/test_figures.py` passed
(4 passed, not skipped). Each named check has a test except
`src/weedlib/solvers.py` has no cut change, which has no test;
`git diff` for that file is empty.
