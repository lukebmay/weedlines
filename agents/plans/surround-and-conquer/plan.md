# Surround and Conquer

**Rank:** 4

**Stage:** algorithm

## Goal

The window opens on Surround and Conquer. On a clear design the
person starts the surround, and that surround matches the
algorithms and preview parts, except the cavern coastline.
That coastline is [`../surround-cavern/plan.md`](../surround-cavern/plan.md).
Conquer is a later stage. Frame, grid, and island-hop still cut.

## Guide

- [`../../architecture/glossary.md`](../../architecture/glossary.md)
- [`../../architecture/preflight.md`](../../architecture/preflight.md)
- [`../../architecture/preview.md`](../../architecture/preview.md)
- [`../../architecture/host.md`](../../architecture/host.md)
- [`../../architecture/algorithms.md`](../../architecture/algorithms.md)
- [`../../architecture/boundary.md`](../../architecture/boundary.md)

## Checks

- The figure check gates every mode, including the surround
  preview. See preflight.
- The surround, when it starts, and the join gap match the
  algorithms, preview, and boundary parts.
- The job names Surround and Conquer when the person has not
  chosen a mode. See the algorithms part.
- Frame, grid, and island-hop still cut a clean design.
- Geometry tests do not need Inkscape. Window tests run
  offscreen when Qt is available.
- The window is on screen before the figure check and before
  the surround build. The host still writes the job first.
