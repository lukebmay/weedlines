# Run log label

**Rank:** 3

**Stage:** stages

## Goal

The pane is labeled Algorithm output. It shows when
a high-level stage starts and when a substage starts,
so the person can see the run move. It does not flood
with one line per segment.

## Guide

- [`../../architecture/runtime.md`](../../architecture/runtime.md)

## Checks

- The label above the log is Algorithm output.
- A stage report and a substage report each add one
  line. An accepted segment does not add a line.
- The pane still shows the run's stdout and stderr.
- The lines do not change the cuts or the step clock.
- What a deliberate log level records does not shrink.
  A reject stays out of the pane unless that level
  asks for it.
