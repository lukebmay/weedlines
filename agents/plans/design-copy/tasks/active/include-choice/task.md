# Include choice

**Status:** ready

## Goal

Include original design is a checkbox, off until
the person turns it on. Apply writes the groups
that choice includes.

## Do

The result is [the host part](../../../../../architecture/host.md).
The history is [the preview part](../../../../../architecture/preview.md).
Do not copy them.

`extensions/inkscape/weedlines_dialog/form.py` and
`extensions/inkscape/weedlines_dialog/__init__.py`
for the checkbox and the Apply return.
`extensions/inkscape/weedlines_host.py` and
`extensions/inkscape/weedlines.py` pass that choice
into the result writer from the result-groups task.
Do not edit that writer. Tests in
`tests/test_window_options.py`.

The label is Include original design. It is off by
default and shows in every mode. A committed change
joins the option history. Pass the border paths the
window already holds. Pass the job records only
when the box is on. When it is off, the result has
no Original design group.

The dialog still receives the job records for the
figure check. Do not pass this result into that
check. Do not rebuild the border, and do not edit
the piece border. The inline path writes the same
groups the result file does.

Do not revive
[design-records](../../inactive/design-records/task.md)
as an always-on design copy. Do not emit a conquer
cut.

## Checks

- The default result has the Border group and the
  Weed lines group, and no Original design group.
- With the checkbox on, Original design is one
  path per job record, `d` copied as stored, with
  no closepath added and no correction id.
- The figure check still reads the job records,
  not this result.
- Cut geometry is unchanged. The checkbox joins
  the option history.
- Offscreen when Qt loads. No Inkscape.

## Note

The developer writes what changed, why, and how it
was checked. The reviewer then writes the summary,
the context worth keeping, and the result.
