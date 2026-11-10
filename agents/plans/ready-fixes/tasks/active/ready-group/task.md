# Ready group

**Status:** ready

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

The developer writes what changed, why, and how it
was checked. The reviewer then writes the summary,
the context worth keeping, and the result.
