# Window clarity

**Rank:** 4

**Stage:** form

## Goal

The form shows only the selected mode's options, in the
display unit, and the person can undo and redo those
values. Arrow kinds are marked with their colors. A run
shows one status and a spinner while it is working. The
run controls match the runtime part.

## Guide

- [`../../architecture/preview.md`](../../architecture/preview.md)
- [`../../architecture/runtime.md`](../../architecture/runtime.md)
- [`../../architecture/boundary.md`](../../architecture/boundary.md)
- [`../../architecture/host.md`](../../architecture/host.md)
- [`../../architecture/algorithms.md`](../../architecture/algorithms.md)

## Checks

- Option visibility, the option history, the arrow swatches,
  and work marks match the preview part. Work marks are a
  later stage and have no tasks yet.
- Lengths on screen match the boundary part. The library
  still receives document user units.
- Start, Restart, Pause, Clear All, and the spinner match
  the runtime part.
- Geometry tests do not need Inkscape. Window tests run
  offscreen when Qt is available.
- This plan starts after responsive-run. It does not add
  the piece border.
