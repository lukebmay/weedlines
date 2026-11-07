# Ready marks

**Status:** in-progress

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

The developer writes what changed, why, and how it was checked.
The reviewer then writes the summary, the context worth keeping,
and the result.
