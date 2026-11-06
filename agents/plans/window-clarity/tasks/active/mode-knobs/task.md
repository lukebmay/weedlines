# Mode knobs

**Status:** ready

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

The developer writes what changed, why, and how it was checked.
The reviewer then writes the summary, the context worth keeping,
and the result.
