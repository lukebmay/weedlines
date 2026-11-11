# Border options

**Status:** ready

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

The developer writes what changed, why, and how it was checked.
The reviewer then writes the summary, the context worth keeping,
and the result.
