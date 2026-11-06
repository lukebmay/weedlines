# Mode knobs

**Status:** done

## Goal

The form shows a length knob, and the output layer name,
only in the mode that uses it.

## Do

`extensions/inkscape/weedlines_dialog.py`. Give the collar
spin and the layer field object names (`collar`,
`layer-name`) so a test can find them.

Show padding for frame, grid, and island-hop. Show grid
spacing for grid. Show the collar for island-hop. Show the
output layer name for those three. Show surround distance
and join gap only for Surround and Conquer. That mode shows
none of the other four.

Leave the mode box, swap, and the four color fields visible
in every mode. Leave Change surround for the run-controls
task. Do not clear a value when its row hides.

## Checks

Offscreen, when Qt loads, in `tests/test_window_surround.py`.

- Surround and Conquer: the two surround lengths visible;
  padding, grid spacing, collar, and the layer name hidden.
- Frame: padding and the layer name visible; grid spacing,
  collar, and both surround lengths hidden.
- Grid: padding, grid spacing, and the layer name visible;
  collar and both surround lengths hidden.
- Island-hop: padding, collar, and the layer name visible;
  grid spacing and both surround lengths hidden.

A value set in one mode is still there when the mode comes
back. Swap and the four color fields stay visible.

## Note

The collar spin is named `collar`. The output layer field is
named `layer-name`. Its label is still "Output layer".

`_show_mode_knobs` shows padding and that layer name for
frame, grid, and island-hop. It shows grid spacing for grid
and the collar for island-hop. Surround and Conquer shows
none of those four. Surround distance and the join gap stay
on the existing surround-only path. Hiding a row does not
change its value. The mode box, swap, the display unit, and
the four color fields stay up in every mode. Change surround
is unchanged, for the run-controls task.

Why: the form was showing every length, and the layer name,
in every mode. The guide shows each one only in the mode
that uses it.

Checked with `QT_QPA_PLATFORM=offscreen pytest
tests/test_window_surround.py tests/test_window_timing.py`:
34 passed in 8.71s. Qt loaded (enaml, PyQt 5.15). No
Inkscape. The new check is `test_mode_knobs_follow_the_mode`.
It opens on Surround and Conquer, visits frame, grid, and
island-hop, and checks the values are still there on the
way back. A grid job also opens with that mode's knobs.
Display-length checks in those two files still pass. Cut
geometry and length conversion were not changed.

## Review

Summary: No defects. The collar spin is named `collar` and
the output layer field is named `layer-name`. Padding and
the layer name show for frame, grid, and island-hop. Grid
spacing shows for grid. The collar shows for island-hop.
Surround and Conquer shows the surround distance and the
join gap, and none of those four. Hiding does not clear a
value. The mode box, swap, the display unit, and the four
color fields stay up. Change surround is unchanged.

Context worth keeping: `_show_mode_knobs` runs once the
opening mode is selected, and again from `_on_mode`. It
only calls `setVisible`. The stored text and spin values
stay put. Surround distance, the join gap, and Change
surround stay in `_show_surround_controls`. The display
unit combo is in neither hide path. `_to_display`,
`_to_user`, and `_show_lengths` were not edited. The pass
is `cr-01.md`.

Result: No defects remain. The named checks passed.
`QT_QPA_PLATFORM=offscreen pytest tests/test_window_surround.py
tests/test_window_timing.py`: 34 passed in 12.57s. Qt loaded
through enaml (PyQt 5.15.14). No Inkscape.
