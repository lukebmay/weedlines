# Make ready

**Rank:** 4

**Stage:** cleanup

## Goal

`2 Make ready to cut` runs the figure check in a child
process and returns at once. When the check finds a
defect, that child writes a ready result. `4 Reimport
last ready cut` places those correction groups, with a
same-color label at each arrow-set origin, above the
design.

## Guide

- [`../../architecture/host.md`](../../architecture/host.md)
- [`../../architecture/preflight.md`](../../architecture/preflight.md)
- [`../../architecture/preview.md`](../../architecture/preview.md)
- [`../../architecture/runtime.md`](../../architecture/runtime.md)

The menu names are in `host.md`. Inkscape sorts the
submenu alphabetically and has no divider. The number
is part of each name. None of the names end in an
ellipsis. The names are `1 Auto generate weedlines`,
`2 Make ready to cut`, `3 Reimport last weedlines`,
and `4 Reimport last ready cut`.

## Checks

- The effect returns without waiting on the check, and
  Inkscape is not asked to apply a document change from
  that effect.
- A defect writes one ready result through
  `write_correction_svg`. A clear check writes none and
  removes a stale ready file.
- `4 Reimport last ready cut` places one layer, `Weedlines
  corrections`, above the open document. Each present
  kind is one group. Each group has one label at that
  kind's origin, in that arrow color, reading `Dangling
  ends`, `Figure overlaps`, or `Self-overlaps`.
- The person's paths are not rewritten. There is no
  design copy and no message box.
- The window's correction return uses that same writer.
- Arrow colors stay `#FF00FF`, `#FF6A00`, and `#00E5FF`.

The fix flow is [`../ready-fixes/plan.md`](../ready-fixes/plan.md).
This plan does not grow those tasks.
