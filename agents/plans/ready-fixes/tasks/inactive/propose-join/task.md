# Propose join

**Status:** done

## Goal

A dangling end is closed by joining the two open
ends of that figure.

## Do

The rule is [the host part](../../../../../architecture/host.md).
Do not copy it.

`src/weedlib/propose.py` and `tests/test_propose.py`
only. The index lines already exist.

Add that join on the proposal record propose-span
started, in the check's defect order. Leave the
self-overlap proposals as they are. Do not start
the weld.

Do not edit the figure check, the arrows, the
surround, the solvers, the piece border, the
surround clip, or the solver clip. Do not call
Inkscape. Do not edit the open document. Do not
seal a cavern, define conquer, or emit a cut.

## Checks

- The dangling-end fix matches the host part.
- Geometry tests do not need Inkscape.

## Note

`propose` now returns a dangling proposal in the check's
order. The path is that figure with a line between the two
open ends of the subpath that owns the endpoint. The endpoint
match is the check's own same-point test. Each self-overlap
stays one proposal with no path. A separate overlap stays out
of the list. The figure path on the check is left as passed.

Why: a dangling end had no join, so the open ends stayed open.

Checked with `python3 -m pytest tests/test_propose.py`:
5 passed. No Inkscape. An open path `M 0,0 L 10,0 L 10,5`
becomes that path plus the line back to `(0, 0)`, and the
check on the result reports no dangling end. An open hole
gains the line between its ends and the outer rectangle
stays. A figure 8 still has no path. Two overlapping squares
produce no proposal.

## Summary

A dangling end gets a path that joins the two open ends of
the subpath that owns that endpoint. The match is the
check's own `_same_point`. The line is `closeSubpath` on a
copy, so the figure path on the check stays as passed. A
hole closes on itself and the outer rectangle stays. Each
`self-overlap` stays one proposal with no path. A separate
overlap stays out. The weld is not started.

## Context worth keeping

`_same_point` is the function the check uses to decide that
two endpoints meet. `_subpath_is_closed` is the function the
check uses before it records a dangling end. Neither
threshold is new in `propose.py`. The two dangling ends of
one open subpath each get that same closed path, in the
check's order. `propose.py` is 67 lines and stays whole.
The figure check, the guide, and `weedlines_svg.py` are not
in this diff. The pass is `cr-01.md`.

## Result

No defect. `python3 -m pytest tests/test_propose.py`:
5 passed in 0.06s. No Inkscape.
