# Job units

**Status:** done

## Goal

The job carries the display unit and the scale of one user
unit, and both the detached host and the inline path hand
them to the window.

## Do

Read both from the document the effect already has, in
`extensions/inkscape/weedlines_svg.py` (`doc_root_attrs`).
Store them on the job's document attrs from
`extensions/inkscape/weedlines.py`. `write_job` already
keeps that dict.

`display_unit` is the unit the document names. Leave it
unset when the document names none. `user_unit_scale` is
how many inches one document user unit is. When the
document gives no scale, store one px (1/96 inch).

Pass both into `run_weedlines_dialog` the same way width,
height, and the viewBox are passed, from
`extensions/inkscape/weedlines_host.py` and from the inline
call in `extensions/inkscape/weedlines.py`. The dialog
keeps them. An unset unit is px on the dialog. Do not
convert the spins in this task.

## Checks

`tests/test_job_records.py`, with no Inkscape process. A
stand-in that names mm and a user unit of one millimeter
stores `mm` and a scale of one millimeter in inches. A
stand-in that names neither stores no display unit and a
scale of 1/96.

`tests/test_window_gate.py`: the host fake and the inline
fake receive both values. The dialog holds them, and a
missing unit is px there.

## Note

`doc_root_attrs` reads the display unit from the document's
`inkscape:document-units` and leaves it unset when the document
names none. `user_unit_scale` is how many inches one user unit
is, from the width or height and the viewBox. No absolute scale
stores one px (1/96 inch). The effect keeps that dict on the
job. The detached host and the inline path pass both into
`run_weedlines_dialog`. The dialog keeps them on
`display_unit` and `user_unit_scale`. An unset unit is px
there. Spins are not converted.

Checked with `QT_QPA_PLATFORM=offscreen pytest
tests/test_job_records.py tests/test_window_gate.py`:
22 passed. Qt loaded. No Inkscape process.

Summary: No defects. The job stores the named display unit
and the inches in one user unit. A document that names none
stores no display unit and a scale of 1/96. The detached
host and the inline path pass both into the dialog. An unset
unit is px on the dialog. The spins are not converted.

Context worth keeping: `doc_root_attrs` reads
`inkscape:document-units` from the namedview, then the root.
It does not use `document_unit`, which would create a
namedview and fill in px. A named `px` stays `px` on the job.
Only the dialog turns a missing unit into px. The scale
comes from the width or height and the viewBox. No absolute
scale stores 1/96. inkex `.scale` is px per user unit and is
used, divided by 96, only when width and viewBox give no
absolute scale. `write_job` keeps the dict. Both call sites
pass `display_unit` and `user_unit_scale` the same way they
pass width, height, and the viewBox. Padding, spacing,
collar, surround distance, and the join gap still use the
raw user-unit counts. `_JOIN_GAP` is still 6.35. Showing
those counts in the display unit is the display-lengths
task. The pass is `cr-01.md`.

Result: No defects remain. The named checks passed.
`QT_QPA_PLATFORM=offscreen pytest tests/test_job_records.py
tests/test_window_gate.py`: 22 passed in 7.73s. Qt loaded.
No Inkscape process.
