# Include choice

**Status:** done

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

Include original design is a checkbox on the
form, off until the person turns it on, and
visible in every mode. Undo and redo of that
checkbox join the option history. Turning it on
does not ask for the border again.

Apply still returns the weed path, the layer
name, and the color. The tuple also carries
`border_d_list` and `records`. `border_d_list`
is the border paths the window already holds.
`records` is the job records only while the box
is on, and omitted while it is off. The dialog
still gives those records to the figure check.
The host and the inline path pass that choice
into the result. The inline path writes the
Weedlines group: Border, Weed lines, and
Original design when records were passed.

Checked with `python3 -m pytest
tests/test_window_options.py`. 13 passed.
Nothing failed. The window tests run offscreen.

The reviewer then writes the summary, the
context worth keeping, and the result.

## Summary

Include original design is off until the person
turns it on, and it shows in every mode. Undo and
redo join the option history. Turning it on does
not ask for the border again. Apply carries the
border paths the window already holds, and the job
records only while the box is on. The default
result is Border and Weed lines. With the box on,
Original design copies each stored `d` and omits a
correction id. The inline path writes those same
groups. The figure check still reads the job
records.

## Context worth keeping

The checkbox is a row with the border controls.
`_on_include_toggled` pushes the option history
and does not call the border ask. Apply watches
`piece_border` and the count stays zero.
`border_d_list` is the serialization of
`state['border_paths']`. `records` is none while
the box is off. The stored panel `d` already ends
in Z, and the copy equals that string. The dialog
still classifies the records it was opened with.
`weedlines_svg.py` and `weedlines_import.py` are
not in this diff. `form.py` is 767 lines. The new
row is the form's own control. No split. The
parked design-records task was not edited. The
pass is `cr-01.md`.

## Result

No defect. `python3 -m pytest tests/test_window_options.py`:
13 passed in 3.03s. No Inkscape. The window was
offscreen.
