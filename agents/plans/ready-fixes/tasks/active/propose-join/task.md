# Propose join

**Status:** ready

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

The developer writes what changed, why, and how it
was checked. The reviewer then writes the summary,
the context worth keeping, and the result.
