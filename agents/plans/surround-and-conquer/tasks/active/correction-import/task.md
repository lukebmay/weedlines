# Correction import

**Status:** ready

## Goal

Import places a correction result on a new layer above the
document, and a weed-line result still imports as it does now.

## Do

- Edit `extensions/inkscape/weedlines_import.py` only.
- When the correction loader returns arrow groups and the file has
  no design copy, add one layer labeled "Weedlines corrections"
  and put those groups in it, above the open document.
- Do not add a design copy. Do not delete or rewrite the person's
  paths. A weed-line result still imports as it does now.
- The rules are the Result section of
  `agents/architecture/host.md`.
- Tests go in `tests/test_correction_import.py`. Skip when inkex
  is missing. Do not require a running Inkscape.

## Checks

- A correction file becomes that one layer and those groups, and
  no design group is added.
- A weed-line file still contributes its design group and its cuts.
- `pytest tests/test_correction_import.py` passes, or skips only
  because inkex is missing.

## Note

The developer writes what changed, why, and how it was checked.
The reviewer then writes the summary, the context worth keeping,
and the result.
