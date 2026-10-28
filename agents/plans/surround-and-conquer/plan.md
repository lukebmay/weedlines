# Surround and Conquer

**Stage:** preflight

## Goal

Every algorithm waits on the shared figure check. The window
shows the subject, the weed area, and any correction arrows, and
the person can send those arrows back to Inkscape. A clean
design still runs frame, grid, and island-hop.

Surround and Conquer's cut subroutines are outside this goal.
The human has not named them.

## Guide

- [`../../architecture/glossary.md`](../../architecture/glossary.md)
- [`../../architecture/preflight.md`](../../architecture/preflight.md)
- [`../../architecture/preview.md`](../../architecture/preview.md)
- [`../../architecture/host.md`](../../architecture/host.md)
- [`../../architecture/algorithms.md`](../../architecture/algorithms.md)

## Checks

- The figure check gates every current mode. See preflight.
- The preview, the swap, and the return actions match the
  preview part.
- The job keeps open paths and fills. Correction import places
  only the arrow groups. See the host part.
- Frame, grid, and island-hop still cut a clean design. See the
  algorithms part.
