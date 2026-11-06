# Display lengths

**Status:** done

## Goal

Lengths on the form are shown in the display unit. The
library and the solvers still receive document user units.

## Do

Use the display unit and `user_unit_scale` stored by the
job-units task. Do not read the SVG again. This is
`extensions/inkscape/weedlines_dialog.py`.

The dropdown starts on the job's unit, or px when that unit
is unset. Its choices are absolute lengths. Percent and em
are not on it. Switching it converts the numbers on screen.
A value that was valid does not get clamped by a range left
over from a millimeter spin.

The unit is a suffix, not part of the label. Take the unit
out of the padding, grid spacing, collar, and join-gap
labels.

Padding, grid spacing, and the collar keep the solver's
user-unit counts. The spin shows those counts converted.
Changing the unit changes the digits. It does not leave the
digits and only change the suffix. `generate_weeds` still
receives the user-unit counts.

The join-gap baseline is a quarter inch in user units under
`user_unit_scale`, then shown in the display unit. It is
not the constant 6.35. Surround distance stays five percent
of the smaller side in user units, shown converted. Both
lengths reach the library in user units.

The surround and timing tests that still mean a millimeter
document should pass that scale, so their geometry stays
put. Add a case whose scale is not one millimeter, and a
case where a padding count is converted on screen and
unchanged for the solver.

## Checks

Offscreen, when Qt loads. Labels for those lengths contain
no unit. The dropdown rejects percent and em, and switching
it converts the shown numbers.

With a one-millimeter user unit and display unit mm, the
join gap shows 6.35 and the library receives 6.35. With no
scale, the library receives 24 (a quarter inch at 96 px per
inch), not 6.35.

A padding of 4 user units still arrives as 4 when the
display unit is not the user unit. The spin does not still
say 4.

`tests/test_window_surround.py` and
`tests/test_window_timing.py`. Do not retarget the cut
tests in `tests/test_window_gate.py`; under the px default
their spin numbers are still user units.

## Note

The dropdown is Inkscape's eight linear units: `px`, `in`,
`ft`, `mm`, `cm`, `m`, `pt`, and `pc`. `yd`, `q`, and `km`
are not choices. They stay in `weedlines_svg._INCHES_PER_UNIT`.
Kilometers were not kept by adding spin decimals. Percent and
em stay off the list.

A job unit of `yd`, `q`, or `km` keeps `dialog.display_unit`
as that name. The combo starts on px, and a one-millimeter
document shows the join gap as 24, not 0. The same fallback
already covered percent and em. Switching still converts the
digits and the ranges. The library still receives document
user units. The SVG is not read again.

Why: on a one-millimeter document, km showed the join gap, a
padding of 4, and the five-percent distance as 0. One step of
that join spin sent 100000 user units to the library, not
6.35.

Checked with `QT_QPA_PLATFORM=offscreen pytest
tests/test_window_surround.py tests/test_window_timing.py`:
33 passed in 12.24s. Qt loaded (PyQt6). No Inkscape. The new
check is `test_dropdown_rejects_yd_q_and_km`. Gate and preview
were not retargeted this pass.

Context worth keeping: Labels are "Padding", "Grid spacing",
"Collar (island-hop)", and "Join gap". The unit is the spin
suffix. A job unit of em keeps `dialog.display_unit` as em,
the combo starts on px, the spin shows 24, and the library
still receives 6.35. No scale sends 24. A centimeter scale
sends 0.635. Surround distance stays 2.5 user units on the
80 by 50 sample. A padding of 4 mm shows about 0.1575 in and
the solver receives 4. An inch edit of 1 sends 25.4.
Switching 200 mm to px shows about 755.9055 and does not
clamp. The combo is the live display.
`tests/test_window_gate.py` and `tests/test_window_preview.py`
were not edited.

`docs/user/surround.md` lines 35–36 and 49 still say **Join
gap (mm)** and that the baseline is always 6.35. Not edited
here. That miss is already an open issues row.

`docs/inkscape-extension.md` lines 81–82 still say the
padding, spacing, and collar spinners are labeled mm. The
labels are "Padding", "Grid spacing", and "Collar
(island-hop)". No test reads that file. Not edited here.

## Review

cr-02. No defect remains.

The dropdown is the eight linear units. `yd`, `q`, and `km`
are not choices and stay in the SVG inch table. Decimals
stay 4. Percent and em stay off the list. A `km` job keeps
`dialog.display_unit`, the combo starts on px, the spin
shows 24, and the library receives 6.35. Switching converts
the digits. The library still receives document user units.

Checked with `QT_QPA_PLATFORM=offscreen pytest
tests/test_window_surround.py tests/test_window_timing.py`:
33 passed in 12.11s. Qt loaded (PyQt6). No Inkscape. An
offscreen `km` start received 6.35. An inch edit of 1 and a
spacing edit of 2 sent 25.4 and 50.8.
