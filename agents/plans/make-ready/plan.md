# Make ready

**Rank:** 4

**Stage:** stub

## Goal

Make ready to cut runs the figure check in a child
process and returns at once. When the check finds a
defect, that child writes a ready result. Reimport last
ready places those correction groups, with a same-color
label at each arrow-set origin, above the design.

## Guide

- [`../../architecture/host.md`](../../architecture/host.md)
- [`../../architecture/preflight.md`](../../architecture/preflight.md)
- [`../../architecture/preview.md`](../../architecture/preview.md)
- [`../../architecture/runtime.md`](../../architecture/runtime.md)

The menu names and this two-step are the sentence to
apply in `host.md` when the stub is implemented. The
user named the menu. Inkscape 1.2.2 sorts the submenu
alphabetically and has no divider. The names are
`Auto generate weedlines…`, `Make ready to cut`,
`Reimport last ready`, and `Reimport last weedlines`.

## Checks

- The effect returns without waiting on the check, and
  Inkscape is not asked to apply a document change from
  that effect.
- A defect writes one ready result through
  `write_correction_svg`. A clear check writes none and
  removes a stale ready file.
- Reimport last ready places one layer, `Weedlines
  corrections`, above the open document. Each present
  kind is one group. Each group has one label at that
  kind's origin, in that arrow color, reading `Dangling
  ends`, `Figure overlaps`, or `Self-overlaps`.
- The person's paths are not rewritten. There is no
  design copy and no message box.
- The window's correction return uses that same writer.
- Arrow colors stay `#FF00FF`, `#FF6A00`, and `#00E5FF`.
