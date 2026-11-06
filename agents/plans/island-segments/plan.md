# Island segments

**Rank:** 4

**Stage:** splits

## Goal

Island-hop reports each accepted segment when it is
accepted, including a hole split. The weed path stays
the same.

## Guide

- [`../../architecture/runtime.md`](../../architecture/runtime.md)
- [`../../architecture/algorithms.md`](../../architecture/algorithms.md)

## Checks

- A frame with a hole reports the hole splits to the
  geometry hook.
- The path island-hop returns stays the same.
- Grid and frame reporting stay as they are.
- Geometry tests do not need Inkscape.
- This plan does not change cut geometry or the
  progress checks.
