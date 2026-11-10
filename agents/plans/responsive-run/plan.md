# Responsive run

**Rank:** 4

**Stage:** responsive

## Goal

The window keeps handling paint and input while the figure
check, the surround, and the solvers run. The run's stdout
and stderr show in the algorithm log. A run that leaves the
window or Inkscape not responding has not met this.

## Guide

- [`../../architecture/runtime.md`](../../architecture/runtime.md)
- [`../../architecture/preview.md`](../../architecture/preview.md)
- [`../../architecture/preflight.md`](../../architecture/preflight.md)

## Checks

- The GUI thread keeps handling events for the whole run.
  Geometry does not run on it. Qt objects the window paints
  stay on it.
- The algorithm log shows that run's stdout and stderr.
- Pause and Clear All take effect during the figure check,
  the surround, and the solvers, at a progress check. A
  check only at the end does not count.
- Geometry tests do not need Inkscape. Window tests run
  offscreen when Qt is available.
- This plan does not change cut geometry or the display
  unit, and it does not paint work marks.
