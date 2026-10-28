# Arrow paths

**Status:** done

## Goal

The library builds one arrow per defect target. The shaft and the
head are path data the preview and the correction result both use.

## Do

- Add `src/weedlib/arrows.py` with `build_arrow_paths`.
- Inputs are the kind (dangling, overlap, or self-overlap), the
  target points, and the design bounds. Minimum y is the top.
- Each arrow has a shaft path, a head path, and that kind's color.
  Origins and colors are Correction arrows in
  `agents/architecture/preview.md`. The colors are not parameters.
- When the target is the origin, the arrow is a short mark whose
  tip is that point.
- Do not edit `src/weedlib/figures.py` or `src/weedlib/solvers.py`.
- Tests go in `tests/test_arrows.py`. No Inkscape. Skip when Qt
  cannot load.

## Checks

- One target yields one shaft and one head. The head tip is the
  target. The shaft starts at that kind's origin.
- A target on the origin still has a visible tip at that point.
- The three colors match the preview part and are not caller
  arguments.
- `pytest tests/test_arrows.py` passes.

## Note

Added `src/weedlib/arrows.py` and `tests/test_arrows.py`.
`build_arrow_paths(kind, targets, bounds)` returns one `ArrowPath`
per target (`shaft`, `head`, `color`). The kind picks the preview
origin and color; color is not an argument. A target on that
origin is a short mark whose head tip stays on the point, because
a shaft from the point to itself would not show. Head length is a
fraction of the design bounds; the guide does not name one.
Checked with `pytest tests/test_arrows.py` (3 passed).

Review summary: the change matches the task. One arrow per target.
The shaft starts at that kind's origin, the head tip is the target,
and the three preview colors are fixed on the kind. A target on
the origin is a short mark whose tip stays on that point.

Context worth keeping: `ArrowPath.shaft` and `.head` are
`QPainterPath` values, not SVG text. The shaft is one open line
ending at the middle of the head base. The head is a closed
triangle. Bounds are a `QRectF`; negative height is normalized so
minimum y stays the top. Head length is `0.06` of the longer side.
The guide does not name one. `figures.py` and `solvers.py` were
not edited.

Result: no defects remain. `pytest tests/test_arrows.py` passed
(3 passed, not skipped). Each named check has a test.
