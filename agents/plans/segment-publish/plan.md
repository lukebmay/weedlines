# Segment publish

**Rank:** 4

**Stage:** publish

## Goal

Each accepted segment is reported when it is accepted, so
the preview can add it during the run. Publishing the
finished path does not report those segments again.

## Guide

- [`../../architecture/runtime.md`](../../architecture/runtime.md)
- [`../../architecture/preview.md`](../../architecture/preview.md)

## Checks

- A grid run reports each hatch segment when it is
  accepted, before the connected-ends pass finishes.
- Each work-rectangle edge is reported once.
- The weed path stays the same.
- Geometry tests do not need Inkscape.
- This plan does not change cut geometry, the progress
  checks, or the display unit.
