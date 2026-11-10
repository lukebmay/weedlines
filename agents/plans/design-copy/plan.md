# Design copy

**Rank:** 3

**Stage:** choice

## Goal

Apply exports the piece border and the weed lines.
Include original design is a checkbox, off by default.
When it is on, the result also has the job's path
records. Import places the included groups inside one
group, each group separate.

## Guide

- [`../../architecture/host.md`](../../architecture/host.md)
- [`../../architecture/preview.md`](../../architecture/preview.md)

## Checks

- The default result has the Border group and the
  Weed lines group, and no Original design group.
- With the checkbox on, Original design is one path
  per job record, `d` copied as stored, with no
  closepath added and no correction id.
- Those groups sit inside the Weedlines group, on one
  layer.
- The figure check still reads the job records, not
  this result.
- A correction result still has no border, no weed
  line, and no original design.
- Cut geometry is unchanged. The checkbox joins the
  option history.
