# Ready writer

**Status:** ready

## Goal

Correction arrows and their labels go out through one
writer. The host does not classify figures and does not
recompute origins.

## Do

Start after ready-marks. This task calls that result.

`write_correction_svg` in
`extensions/inkscape/weedlines_svg.py` is the only
correction writer. It adds one text element at the label
point, in the arrow color. Do not add a second writer.

The window correction return in
`extensions/inkscape/weedlines_dialog/` uses that writer.
The label point is the one from `build_correction_marks`.
Do not call `classify_figures` on the GUI thread. Do not
classify in the host. Do not recompute origins in the
host.

## Checks

- `tests/test_correction_result.py` and
  `tests/test_window_return.py` pass.
- A present kind gets one text element at that kind's
  origin, in that arrow color, with the label text from
  the marks.
- A kind with no arrows is still omitted.
- The host has no second origin table and no figure
  classification.

## Note

The developer writes what changed, why, and how it was checked.
The reviewer then writes the summary, the context worth keeping,
and the result.
