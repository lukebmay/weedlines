# Propose span

**Status:** ready

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

The developer writes what changed, why, and how it
was checked. The reviewer then writes the summary,
the context worth keeping, and the result.
