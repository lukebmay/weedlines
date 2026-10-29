# Surround and Conquer

**Rank:** 3

**Stage:** algorithm

## Goal

The window opens on Surround and Conquer. On a clear design the
surround follows the surround distance in the preview, and the
mode does not continue until the person approves that surround.
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
- The surround, the surround distance, and the approval match
  the algorithms and preview parts.
- The job names Surround and Conquer when the person has not
  chosen a mode. See the algorithms part.
- Frame, grid, and island-hop still cut a clean design.
- Geometry tests do not need Inkscape. Window tests run
  offscreen when Qt is available.
