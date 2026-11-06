# Display lengths

**Status:** ready

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

The developer writes what changed, why, and how it was checked.
The reviewer then writes the summary, the context worth keeping,
and the result.
