# Propose span

**Status:** waiting

Blocked. The host part names a smooth stack, a corner
stack, and a larger self-overlap in words, and it names
no angle and no gap fraction. The figure check's kind
`self-overlap` does not make that split. Do not invent
the number.

## Goal

The library proposes a replacement for stacked nodes
on a smooth span, and no replacement for a larger
self-overlap the person may keep.

## Do

The rule is [the host part](../../../../../architecture/host.md).
Do not copy it.

New file `src/weedlib/propose.py`. One index sentence
in `src/weedlib/README.md`. Tests in
`tests/test_propose.py`, and one index sentence in
`tests/README.md`.

`propose` takes the figure check the caller already
has. It does not run the check again and it does not
change it. Each proposal names the defect it answers
and either a replacement path or none. Keep the
check's defect order. Later tasks in this file use
that same record.

A stacked self-overlap on a smooth span gets the
replacement the host part names for that case. A
larger self-overlap, including a figure 8, gets no
replacement. Skip a corner stack: do not emit a
proposal for it, and do not add a test that it has
none. The corner task adds that proposal.

Do not start the join or the weld. Do not add a
second module. Do not edit the figure check, the
arrows, the surround, the solvers, the piece border,
the surround clip, or the solver clip. Do not call
Inkscape. Do not edit the open document. Do not seal
a cavern, define conquer, or emit a cut.

## Checks

- The smooth-span fix matches the host part.
- A figure 8 can be kept with no fix.
- Geometry tests do not need Inkscape.

## Note

The guide has no number for the split between a smooth stack,
a corner stack, and a larger self-overlap. The figure check
records every crossing as kind `self-overlap` and a target.
That kind cannot make the split.

Removed the cosine of 20 degrees, the quarter-gap fraction,
the node gap, and the collinear path builder. `propose` now
returns one proposal per self-overlap, in the check's order,
with no path. Dangling ends and separate overlaps stay out.
No self-overlap is dropped by a measurement.

The smooth-span fix still cannot be chosen without a number
the guide does not name.

Checked with `python3 -m pytest tests/test_propose.py`:
2 passed. No Inkscape. Those tests do not choose the
smooth-span fix.

## Summary

`propose(check)` walks the defects the caller already has.
It does not run the check again and it does not change it.
Each `self-overlap` is one proposal with no path, in the
check's order. Dangling ends and separate overlaps stay out.
The cosine of 20 degrees, the quarter-gap fraction, the node
gap, and the collinear path builder are gone. No new number
classifies a `self-overlap`. The tests do not treat a smooth
span as chosen.

The smooth-span task checks do not pass. Every self-overlap
is kept, so the host part's replacement for a stacked smooth
span is not built.

## Context worth keeping

The check already uses three kinds. A dangling end is
`dangling`. A separate-figure overlap is `overlap`. A
crossing of one figure is `self-overlap`. Those strings are
already distinct, so a later join or weld can follow the
kind without a new measurement. This pass does not start
those tasks. The figure check and the guide are not in this
diff. The pass is `cr-02.md`.

## Result

The defect is gone. No number is the decision.

The smooth-span task checks do not pass. The smooth-span fix
still cannot be chosen.

`python3 -m pytest tests/test_propose.py`: 2 passed in 0.04s.
No Inkscape.
