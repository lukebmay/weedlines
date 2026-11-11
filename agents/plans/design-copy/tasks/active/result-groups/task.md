# Result groups

**Status:** ready

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

The developer writes what changed, why, and how it
was checked. The reviewer then writes the summary,
the context worth keeping, and the result.
