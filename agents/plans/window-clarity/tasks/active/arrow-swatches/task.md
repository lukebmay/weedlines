# Arrow swatches

**Status:** ready

## Goal

Each defect kind named under the preview is preceded by a
swatch of that arrow's color.

## Do

`extensions/inkscape/weedlines_dialog.py`, on the return
line. The words stay dangling ends, figure overlaps, and
self-overlaps, in the label color. A swatch of that kind's
arrow color sits before each name. Take the color from the
arrow the library already returns. Do not edit the library
color. The self-overlap color stays `#00E5FF`.

The line and the two return actions stay under the preview.
They do not become a popup.

## Checks

Offscreen, when Qt loads. Update
`tests/test_window_return.py` and the return-line assertion
in `tests/test_window_timing.py`.

The words are still there. Each kind name has a swatch
before it, matching that arrow's color, and the words are
not recolored. The self-overlap swatch is `#00E5FF`. A
clear check still has an empty line and no correction
action.

## Note

The developer writes what changed, why, and how it was checked.
The reviewer then writes the summary, the context worth keeping,
and the result.
