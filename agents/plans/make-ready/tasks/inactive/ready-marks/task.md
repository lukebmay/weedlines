# Ready marks

**Status:** done

## Goal

The library has one check-and-arrow result. It does not
write SVG, and it does not read the document.

## Do

Library only. The contract is the Library section of
[`../../../stages/stub.md`](../../../stages/stub.md).

`src/weedlib/ready.py` `build_correction_marks(records)`
calls `classify_figures` in `src/weedlib/figures/` once
and `build_arrow_paths`. No swap argument.

`arrow_origin` stays in `src/weedlib/arrows.py`. It is
the origin `build_arrow_paths` already uses. Do not copy
the corner table.

The result carries the check, the bounds, the arrow
paths for each kind that has a target, and one label per
such kind. The text is `Dangling ends`, `Figure
overlaps`, or `Self-overlaps`. The color is that kind's
arrow color. The point is the kind origin.

Do not add `ready` to `weedlib` `__all__` unless a
current caller needs it. Add tests for the marks. Do not
edit the host.

## Checks

- The new mark tests pass.
- A kind with no target has no arrow paths and no label.
- `build_correction_marks` has no swap parameter.
- `ready.py` does not write SVG and does not import the
  host or the dialog.
- Arrow colors stay `#FF00FF`, `#FF6A00`, and `#00E5FF`.

## Note

`src/weedlib/ready.py` adds `build_correction_marks(records)`.
It calls `classify_figures` once, takes design bounds from
`subject_weed_regions` with swap fixed off, and calls
`build_arrow_paths` only for a kind that has a target. That
kind gets one label: `Dangling ends`, `Figure overlaps`, or
`Self-overlaps`. The color is the arrow color. The point is
`arrow_origin`. A kind with no target is omitted. The function
takes no swap argument, writes no SVG, and does not import the
host, the dialog, or an SVG writer. `ready` is not in
`weedlib` `__all__`.

`arrow_origin(kind, bounds)` is in `src/weedlib/arrows.py`.
It is the origin helper `build_arrow_paths` uses. The corner
choice still reads the existing kind table. There is no second
corner table.

`tests/test_ready.py` covers a clear check, which has no labels,
and one dangling kind, which has one `Dangling ends` label at
the dangling origin in `#FF00FF`. `tests/README.md` has one
sentence for that file. `tests/test_arrows.py` was not weakened.

Checked with `pytest tests/test_ready.py tests/test_arrows.py`:
5 passed. `build_correction_marks` parameters are `records`
only. `ready.py` imports `__future__`, `dataclasses`, `arrows`,
and `figures`.

Summary: No defects. The library returns one check, the design
bounds, arrows for kinds that have a target, and one label per
such kind. The named tests passed.

Context worth keeping: `build_correction_marks(records)` calls
`classify_figures` once. Swap is not a parameter. Bounds come
from `subject_weed_regions` with swap fixed off, and that call
does not move the bounds. A kind with no target is omitted.
Label text is `Dangling ends`, `Figure overlaps`, or
`Self-overlaps`. The color is the arrow color from `_KINDS`:
`#FF00FF`, `#FF6A00`, and `#00E5FF`. The point is
`arrow_origin`, which `build_arrow_paths` also uses. The
corner table stays in `_KINDS`. `ready.py` does not write SVG
and does not import the host, the dialog, or an SVG writer.
`ready` is not in `weedlib` `__all__`. The host, the dialog,
the solvers, and the surround were not edited. The pass is
`cr-01.md`.

Result: No defects remain. The named checks passed.
`QT_QPA_PLATFORM=offscreen pytest tests/test_ready.py
tests/test_arrows.py`: 5 passed in 0.03s. Qt loaded. No bug
outside this change.
