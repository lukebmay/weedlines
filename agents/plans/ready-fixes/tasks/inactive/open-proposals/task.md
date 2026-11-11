# Open proposals

**Status:** waiting

Blocked. The proposal window does not exist yet.
That window is waiting on propose-span and
propose-corner.

## Goal

A defect opens the proposal window after the ready
file is written. The effect has already returned,
so Inkscape is not held while the person decides.

## Do

The approval is [the host part](../../../../../architecture/host.md).
Inkscape staying free is [the runtime part](../../../../../architecture/runtime.md).
Do not copy them.

`extensions/inkscape/weedlines_ready.py` and
`tests/test_ready_menu.py`.

`ReadyEffect.effect` still only snapshots the job
and spawns, then returns without a document
change. The child writes the ready file through
the correction writer when the check has a defect,
asks the library for the proposals, then opens the
proposal window. That ask is not on the window's
GUI thread. A clear check writes no ready file,
removes a stale one, and does not open the window.

Do not open the weed-line host. Do not insert
arrows into the open document. Do not auto-correct
a clear check. Do not convert objects to paths.

## Checks

- A clear check still writes no ready file and does
  not open the window.
- The effect does not hold Inkscape while the
  person decides.

## Note

The developer writes what changed, why, and how it
was checked. The reviewer then writes the summary,
the context worth keeping, and the result.
