# Propose weld

**Status:** ready

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

The developer writes what changed, why, and how it
was checked. The reviewer then writes the summary,
the context worth keeping, and the result.
