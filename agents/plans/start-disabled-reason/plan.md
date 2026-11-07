# Start disabled reason

**Rank:** 4

## Goal

When defects disable Start, the person can tell why
without the status saying they are ready to start.

## Guide

- [`../../architecture/preview.md`](../../architecture/preview.md)
- [`../../architecture/runtime.md`](../../architecture/runtime.md)

## Checks

- Start that is disabled because the figure check found
  a defect has a tooltip that points at the marked problems.
- The line under the preview stays in the layout.
- The status words stay ready, working, paused, and done.
- Start disabled because a step is running is unchanged.
