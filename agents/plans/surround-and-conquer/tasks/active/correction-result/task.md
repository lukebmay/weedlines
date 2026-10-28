# Correction result

**Status:** ready

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

The developer writes what changed, why, and how it was checked.
The reviewer then writes the summary, the context worth keeping,
and the result.
