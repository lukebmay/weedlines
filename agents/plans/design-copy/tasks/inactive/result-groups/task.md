# Result groups

**Status:** done

## Goal

A weed-line result holds the Border group and the
Weed lines group inside the Weedlines group. The
original design is included only when the caller
asks for it.

## Do

The rule is [the host part](../../../../../architecture/host.md).
Do not copy it.

`extensions/inkscape/weedlines_svg.py`,
`extensions/inkscape/weedlines_job.py`, and
`extensions/inkscape/weedlines_import.py`. Tests
in `tests/test_cut_stroke.py`,
`tests/test_correction_import.py`, and
`tests/test_correction_result.py`.

The result is one group labeled Weedlines, on one
layer. Inside it, the groups that were included.
The default is Border and Weed lines. No Original
design group, and no Weedlines design group.
`keep_d` is not that group.

Border path data is what the caller passes. Do not
build it, and do not edit the piece border. Those
paths use the same stroke as the cuts. Cut `d`
values stay as the caller passed them.

When the caller includes the original design, add
one Original design group. One path per job
record, in that order, `d` copied as stored. Do
not add a closepath. Omit a record whose id starts
with `weedlines-correction`, and do not write a
Weedlines corrections group into this result.

A correction result still has no border, no weed
line, and no original design. Import of a ready
file stays as it is. Import of a weed-line result
places the Weedlines group on one layer and does
not delete the person's paths.

Do not edit the window. Do not give this result to
the figure check. Do not revive
[design-records](../../inactive/design-records/task.md)
as an always-on design copy. Do not emit a conquer
cut.

## Checks

- The default result has the Border group and the
  Weed lines group, and no Original design group.
- When the caller includes it, Original design is
  one path per job record, `d` copied as stored,
  with no closepath added and no correction id.
- Those groups sit inside the Weedlines group, on
  one layer.
- A correction result still has no border, no weed
  line, and no original design.
- Cut geometry is unchanged.
- The figure check still reads the job records,
  not this result.

## Note

The weed-line SVG is one layer. Inside it, one
group labeled Weedlines holds Border and Weed
lines. `write_result` takes `border_d_list` and
`records`. Both default to omitted, so a caller
that passes neither gets those two groups.
Border path data is `border_d_list`, drawn with
the cut stroke. Cut `d` values are the list the
caller passes. When `records` is passed, Original
design is one path per record, in that order,
`d` copied as stored. A record whose id starts
with `weedlines-correction` is omitted. `keep_d`
stays on the JSON.

A correction result stays the ready file: arrow
groups for the kinds that have an arrow. Import
of a weed-line result places the Weedlines group
on one new layer and leaves the open paths.
Import of a ready file places the corrections
layer.

The figure check runs on the job records. The
writer stayed in `weedlines_svg.py` (600
lines). The groups are that writer's job.

Checked with `python3 -m pytest
tests/test_cut_stroke.py
tests/test_correction_import.py
tests/test_correction_result.py`. 27 passed.
Nothing failed.

The reviewer then writes the summary, the
context worth keeping, and the result.

## Summary

The default weed-line result is one layer. Inside
it, one group labeled Weedlines holds Border and
Weed lines. Original design is absent unless
`records` is passed. `keep_d` stays on the JSON
and is not that group. There is no Weedlines
design group. Border path data and cut `d` values
are the lists the caller passes, and both use the
cut stroke. A passed record list is one path per
record, `d` copied as stored, with a correction
id omitted and no closepath added. A correction
result is still arrow groups only. Import of a
weed-line result places the Weedlines group on
one new layer and leaves the open paths.

## Context worth keeping

Both new arguments default to omitted. The host
Apply call does not pass `records`, so that call
still writes Border and Weed lines only. The
checkbox belongs to include-choice. The window
was not edited. The figure check in the test
reads the job records, not the result SVG.
`weedlines_svg.py` is 600 lines. The new groups
are that result writer. No split. The parked
design-records task was not edited. The pass is
`cr-01.md`.

## Result

No defect. `python3 -m pytest tests/test_cut_stroke.py tests/test_correction_import.py tests/test_correction_result.py`:
27 passed in 0.92s. No Inkscape.
