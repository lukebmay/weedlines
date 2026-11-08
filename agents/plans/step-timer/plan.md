# Step timer

**Rank:** 4

**Stage:** timer

## Goal

The window shows how long each started step spent
working, as the runtime part says. The library does
not own the clock.

## Guide

- [`../../architecture/runtime.md`](../../architecture/runtime.md)
- [`../../architecture/preview.md`](../../architecture/preview.md)

## Checks

- Each started step has its own working time, shown
  with that step's status. A phase name is not its own
  time. Conquer has no time while its Start stays
  disabled.
- The time advances only while the step is working. It
  holds while paused. Restart starts that step from
  zero and discards later steps' times with their
  lines. Clear All discards the times with the lines.
- Ticking the clock does not run geometry and does not
  change a cut. The time is not only a log line.
- Window tests run offscreen when Qt is available.
- The user page that mentions the run matches the
  runtime part.
