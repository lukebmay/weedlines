# Propose weld

**Status:** done

## Goal

Figures that overlap are welded into one path.

## Do

The rule is [the host part](../../../../../architecture/host.md).
Do not copy it.

`src/weedlib/propose.py` and `tests/test_propose.py`
only. The index lines already exist.

The library welds the overlapping figures by the
same union Inkscape uses when it unions and
combines. Do not launch Inkscape to do it. Use the
proposal record and the defect order already in
this file. Leave the other proposals as they are.

Do not edit the surround, the solvers, the piece
border, the surround clip, or the solver clip. Do
not edit the figure check or the arrows. Do not
edit the open document. Do not seal a cavern,
define conquer, or emit a cut.

## Checks

- The overlap fix matches the host part.
- Geometry tests do not need Inkscape.

## Note

Removed `_without_nesting_parents` and `_nests`. They dropped
a figure by testing area outside, and the overlap record does
not name the pair. The weld is `QPainterPath.united` of every
painted area that contains the target, with `OddEvenFill`. A
containing square stays in that union. Dangling joins stay.
Each self-overlap stays one proposal with no path.

Why: the drop was a measurement the check does not store.

Checked with `python3 -m pytest tests/test_propose.py`:
5 passed. No Inkscape. The `20×20` border test is gone.
Two squares `0,0–4,4` and `2,2–6,6` still become one path
that contains `(1,1)`, `(3,3)`, and `(5,5)` and leaves
`(5,1)` and `(1,5)` outside. A figure 8 still has no path.

## Summary

`_without_nesting_parents` and `_nests` are gone. The
weld is `QPainterPath.united` of every painted area that
contains the target, with `OddEvenFill`. A figure stays
in when its painted area contains that target. No
area-outside test drops a containing square. Dangling
joins stay. Each `self-overlap` stays one proposal with
no path. The tests do not encode a nesting rule.

## Context worth keeping

The overlap record is still only a kind and a target.
Membership is that target: a painted area that contains
it is in the union, and one that does not is out. That
is not a new measurement. `_outside_fill` is not called.
The `20×20` border test is gone. `propose.py` is 85
lines. The figure check and the guide are not in this
diff. The pass is `cr-02.md`.

## Result

The defect is gone. No number decides which figure stays
out.

`python3 -m pytest tests/test_propose.py`: 5 passed in
0.05s. No Inkscape.
