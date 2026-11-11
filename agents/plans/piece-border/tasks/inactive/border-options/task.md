# Border options

**Status:** done

## Goal

The form shows Border Padding, Border Width, and
Border Rounded Corners in every mode, and Border
Corner Radius while that box is on.

## Do

Edit only
`extensions/inkscape/weedlines_dialog/form.py` and
`tests/test_window_border.py`. Do not edit the
library, the ask, or the run controls. Do not
forward `corner_radius` through the window ask.
That work is
[border-ask](../../../../border-ask/plan.md).

The labels are **Border Padding**, **Border
Width**, **Border Rounded Corners**, and **Border
Corner Radius**. Hide the radius while the box is
off. The radius starts at one quarter of an inch.
The window does not allow it below zero or above
half the shorter side of the inner rectangle.

The stored lengths and `change_piece_length` come
from the border-paint task. Border padding, the
checkbox, and the radius call that entry. The
border width calls it so the ask is for the border
only. Do not build or clip the rectangles here.
Do not put the radius on the ask.

The ask forwards `lengths['corner_radius']` whenever
that key is set. The window keeps the number while
it is open, including while the box is off. The
radius applies only while the box is on. A kept
number that is not being applied must not sit on
that key.

Keep the values while the window is open, including
the radius while the box is off. A committed change
joins the option history the other lengths already
use. These controls do not bring back frame padding,
grid spacing, the collar, or the layer name. Do not
remove island-hop.

Do not edit `docs/` or `README.md`.

## Checks

- The form shows Border Padding, Border Width, and
  Border Rounded Corners in every mode. Border Corner
  Radius shows only while the box is on, and it starts
  at one quarter of an inch.
- Changing border padding, the box, or the radius asks
  for the border and, when a surround is showing, for
  the surround. Changing the border width asks for the
  border only.
- Undo and redo cover a committed change to either
  length, the checkbox, and the radius. Frame padding,
  grid spacing, the collar, and the layer name stay as
  they are. Island-hop stays.
- Offscreen, when Qt loads, in
  `tests/test_window_border.py`. No Inkscape.

## Note

The form shows Border Padding, Border Width, and
Border Rounded Corners in every mode. Border Corner
Radius is hidden while that box is off. The kept
number starts at one quarter of an inch, in user
units, and the spin stops at zero and at half the
shorter side of the inner rectangle.

`lengths['border_radius']` holds that number for the
whole visit, including while the box is off.
`lengths['corner_radius']` is set only while the box
is on, which is when the ask forwards it. Padding,
the checkbox, and the radius call
`change_piece_length`, so the border is asked again
and a surround that is already showing is asked
again. Border width calls it for the border only.
A committed change joins the option history the
other lengths use. Frame padding, grid spacing, the
collar, the layer name, and island-hop stay as they
were. The form does not build the rectangles.

Why: the form had no border controls, and
`change_piece_length` returned for any key other
than padding or width, so a corner radius never
became the value the ask already forwards.

Checked with `python3 -m pytest tests/test_window_border.py`:
11 passed. No Inkscape. The window was offscreen.

Summary: No defect. The form shows Border Padding, Border
Width, and Border Rounded Corners in every mode. Border
Corner Radius is hidden while that box is off. The kept
number starts at one quarter of an inch, `_QUARTER_INCH`
divided by the document scale, the same count as the join
gap. It is not 6.35 and not a bare 0.25.
`lengths['border_radius']` holds it for the whole visit.
`lengths['corner_radius']` is set only while the box is
on. The spin stops at zero and at half the shorter side
of the inner rectangle, and a padding change runs that
cap again. Padding, the checkbox, and the radius ask for
the border and, when a surround is showing, for the
surround. Border width asks for the border only. Undo
and redo cover those committed changes. Frame padding,
grid spacing, the collar, the layer name, and island-hop
stay. The form does not build the rectangles.

`form.py` is 738 lines. The new code is still the form.
No split.

Context worth keeping: The ask already forwards
`lengths['corner_radius']` whenever that key is set, so
the key stays off while the box is off and holds the
kept number while the box is on. The opening cap is what
the test reads. A later padding change uses the same
clamp, and that second maximum is not a separate
assertion. The parent's `piece_border` watch stays
empty. The diff is `form.py`,
`tests/test_window_border.py`, and this note. The pass
is `cr-01.md`.

Result: No defect. `python3 -m pytest
tests/test_window_border.py`: 11 passed in 7.70s.
PyQt6 6.7.1. No Inkscape. The window was offscreen.
