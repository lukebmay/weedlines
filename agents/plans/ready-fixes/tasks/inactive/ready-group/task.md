# Ready group

**Status:** done

## Goal

An approved set is one group, labeled Ready fixes,
in the ready file. Reimport places that group and
does not delete the original paths.

## Do

The rule is [the host part](../../../../../architecture/host.md).
Do not copy it.

`extensions/inkscape/weedlines_svg.py`,
`tests/test_correction_result.py`, and
`tests/test_correction_import.py`.

Add a writer next to `write_correction_svg`. It
puts the approved replacement paths into the ready
file as one group labeled "Ready fixes" and leaves
the arrow groups in place. When there are no
approved paths, it does not add the group. Stay in
this file. The loader returns that group with the
arrow groups, so reimport places it on the
Weedlines corrections layer.

An arrow-only ready file stays arrow-only. Reimport
of weed lines still refuses a ready file. Do not
open a window. Do not edit `weedlines_ready.py`.
Do not write a ready file for a clear check.

## Checks

- Reimport places an approved Ready fixes group and
  does not delete the original paths.

## Note

`write_ready_fixes` in `extensions/inkscape/weedlines_svg.py`
writes the approved paths into the ready file as one group
labeled Ready fixes, id `weedlines-correction-ready`. Arrow
groups stay. A later call replaces that group. Empty paths
leave the arrow file as it was, and a missing file stays
missing. `load_correction_svg_groups` returns the group with
the arrow groups. Reimport places it on the Weedlines
corrections layer. The open path stays on Layer 1 with its
`d` unchanged. Weed-line reimport of that ready file still
raises `AbortExtension`. Approved paths are fill none, with
stroke width 0.25.

Why: an approved set had no group in the ready file, so
reimport placed only the arrows.

Checked with `python3 -m pytest tests/test_propose.py
tests/test_correction_result.py tests/test_correction_import.py`:
14 passed, 0 failed. No window. No Inkscape process.

## Summary

`write_ready_fixes` writes the approved paths as one group
labeled Ready fixes, id `weedlines-correction-ready`. The
arrow groups stay. A later call replaces that group. Empty
path data leaves the arrow file as it was and does not
create a missing file. The loader returns the group with
the arrow groups. Reimport places it on the Weedlines
corrections layer and leaves the open path on Layer 1.
Weed-line reimport of that ready file still raises
`AbortExtension`.

## Context worth keeping

The writer stays next to `write_correction_svg`. Approved
paths are fill none and stroke width 0.25.
`weedlines_ready.py` is not in this diff. The writer does
not open a window and does not write a file when there is
nothing to add. `weedlines_svg.py` is 567 lines. The new
writer is the same job as the correction writer. No split.
The loader's default file is still the weed-line result,
and the stroke is black. Neither fails a named check. The
pass is `cr-01.md`.

## Result

No defect. `python3 -m pytest tests/test_propose.py tests/test_correction_result.py tests/test_correction_import.py`:
14 passed in 0.11s. No Inkscape.
