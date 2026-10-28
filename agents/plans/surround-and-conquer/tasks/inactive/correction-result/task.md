# Correction result

**Status:** done

## Goal

A correction result holds only arrow groups. The weed-line result
stays the file written today.

## Do

- In `extensions/inkscape/weedlines_svg.py`, write a correction SVG
  from shaft and head paths. One group per kind that has at least
  one arrow, and only those kinds. Labels, ids, shaft fill, and
  head color are the Result section of
  `agents/architecture/host.md`. No design copy.
- Add a loader that returns those groups. Do not change what the
  weed-line loader returns for a design-plus-cuts file.
- In `extensions/inkscape/weedlines_job.py`, add a correction
  writer that stores that SVG and its JSON. Do not change
  `write_result`.
- Tests go in `tests/test_correction_result.py`. No Inkscape.
- Do not edit import or the dialog.

## Checks

- A kind with no arrows has no group. The file has no design copy.
  Each path id starts with `weedlines-correction`.
- A shaft has no fill. A head uses that arrow's color.
- An open shaft is not given a closepath in the file.
- `write_result` still writes a design group and cut paths.
- `pytest tests/test_correction_result.py` passes without Inkscape.

## Note

Added a correction result beside the weed-line result. `write_result`
is unchanged and still writes the design group and the cut paths.

`write_correction_result(arrows, doc_attrs=None, meta=None)` in
`weedlines_job.py` stores `last_result.json` and `last_result.svg`.
`arrows` maps `dangling`, `overlap`, and `self-overlap` to
`ArrowPath` values from `build_arrow_paths`. A kind with no arrows
is omitted. The SVG has no design copy. Group labels are "Dangling
ends", "Figure overlaps", and "Self-overlaps". Each path id starts
with `weedlines-correction`. A shaft is `fill:none` and stroked in
that arrow's color. A head is filled with that color. An open shaft
is serialized with no closepath. The guide names no shaft width;
stroke-width 0.25 matches the weed-line strokes in this file.

The import task should call `load_correction_svg_groups(path)`. It
returns those group elements, or `[]` when the file is missing or is
a design-plus-cuts file. `load_result_svg_groups` is unchanged.

Checked with `pytest tests/test_correction_result.py` (4 passed).
No Inkscape.

Summary: No defects. A correction result is arrow groups only.
`write_result` still writes the design group and the cut paths.
A shaft has no fill and is stroked in that arrow's color. A head
uses that color. An open shaft has no closepath.

Context worth keeping: `write_correction_result` stores
`last_result.json` and `last_result.svg`. The import task should
call `load_correction_svg_groups`. It returns the kind groups, or
`[]` for a missing file or a design-plus-cuts file.
`load_result_svg_groups` is unchanged. Import and the dialog were
not edited. Preview colors on the shaft stroke are dangling
`#FF00FF`, overlap `#FF6A00`, and self-overlap `#00E5FF`. The
named fill test does not read the stroke, so a wrong stroke color
would still pass it. The written file uses the arrow color, so
that is not a broken check. Stroke width `0.25` is not named; it
matches the weed-line strokes in this file. The pass is `cr-01.md`.

Result: No defects remain. The named checks passed.
`pytest tests/test_correction_result.py` passed (4 passed, not
skipped, no Inkscape).
