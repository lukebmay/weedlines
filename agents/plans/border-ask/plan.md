# Border ask

**Rank:** 4

**Stage:** ask

## Goal

When the dialog has a border corner radius, the
border ask, the surround ask, and the solver ask
pass that radius to the library. When it does not,
those calls stay as they are. The form control
stays on the piece-border plan.

## Guide

- [`../../architecture/algorithms.md`](../../architecture/algorithms.md)
- [`../../architecture/preview.md`](../../architecture/preview.md)
- [`../../architecture/boundary.md`](../../architecture/boundary.md)
- [`../../architecture/runtime.md`](../../architecture/runtime.md)

## Checks

- A radius the dialog already has reaches
  `piece_border`, `build_surrounds`, and
  `generate_weeds`.
- No radius leaves those calls on the square
  border they already use.
- The form is not edited. The library geometry
  is not edited.
- The asks stay off the GUI thread.
- Window or request tests do not need Inkscape.
  Offscreen when they open a window.
