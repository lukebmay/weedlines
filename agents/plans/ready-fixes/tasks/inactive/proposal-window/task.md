# Proposal window

**Status:** waiting

Blocked. propose-span and propose-corner are waiting.
The host part names no number that separates a smooth
stack from a corner stack, and the figure check does
not either. This window waits until those proposal
tasks are done. Do not invent the number.

## Goal

The window shows each proposed fix. The person
approves that fix, approves every remaining fix,
or declines it.

## Do

The rule is [the host part](../../../../../architecture/host.md).
Do not copy it.

New file
`extensions/inkscape/weedlines_dialog/proposals.py`.
One index sentence in
`extensions/inkscape/weedlines_dialog/README.md`.
Tests in `tests/test_window_propose.py`, and one
index sentence in `tests/README.md`.

Show each proposal before it is kept. The person
approves that fix, approves every remaining fix,
or declines it. A decline adds no replacement and
does not remove the arrow. An approval of a
replacement adds that library path to the Ready
fixes group through the writer in
`weedlines_svg.py`. Do not edit that file. A
proposal with no path, including a figure 8, can
be kept with no fix: approving it adds nothing.

Paint the library path against the original. Do
not invent a path. Do not compute geometry. Do not
start a solver, write a weed-line result, or edit
the open document. This is not the weed-line
window. Do not mount it on Start, the surround, or
conquer.

Not this task: auto-correct of a clear check,
converting objects to paths, or inserting arrows
from the effect.

## Checks

- The person can approve one fix, approve all
  remaining fixes, or decline one and keep it.
- The approval and the decline match the host part.
- A figure 8 can be kept with no fix.
- Window tests run offscreen when Qt is available.

## Note

The developer writes what changed, why, and how it
was checked. The reviewer then writes the summary,
the context worth keeping, and the result.
