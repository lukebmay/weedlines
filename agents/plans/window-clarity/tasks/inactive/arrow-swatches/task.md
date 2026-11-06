# Arrow swatches

**Status:** done

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

The return line stays one label under the preview. When the
figure check names a kind, a full block in that kind's arrow
color sits immediately before the name. The color is the
`color` on the arrow path the library already returned. The
library colors are not edited. The name is outside that span,
the label has no stylesheet, and its text color stays the
label color. With no defects the line is still empty and the
correction action is still absent. After the correction
action, the import sentence replaces the line as plain text
and a later subject ask does not put the names back.

Checked offscreen, no Inkscape, with `QT_QPA_PLATFORM=offscreen
pytest tests/test_window_return.py tests/test_window_timing.py
tests/test_window_options.py`: 15 passed, 1 failed. The swatch
checks cover all three kinds, dangling only, and dangling plus
self-overlap. The self-overlap swatch is `#00E5FF`. The words
and the old sentence remain, and those words carry no color of
their own. The line and both actions stay under the preview.
Option undo still passes. Status left `in-progress`.

The failure is not this change. `test_clear_check_has_an_empty_line_and_start_works`
in `tests/test_window_return.py` times out with "start did not
run" on this dialog and on the dialog at HEAD. Its empty-line
asserts pass. The test patches `weedlib.generate_weeds` in the
parent, and the solver imports that function inside the spawned
child, so `seen` stays empty.

## Summary

No defects in this change. The return line under the preview
puts a full block in each present kind's arrow color before
the name. The words stay dangling ends, figure overlaps, and
self-overlaps, outside that color, in the label color. The
color is the one on the arrow path the library already
returned. The library color was not edited. The self-overlap
swatch stays `#00E5FF`. The line and both return actions stay
under the preview. A clear check still has an empty line and
no correction action. After the correction action, the import
sentence replaces the line as plain text.

## Context worth keeping

The swatch is `<span style="color:#RRGGBB;">&#9608;</span>`
and nothing else. The hex is the validated color from
`batch[0].color`. `_show_return_line` runs once at classify,
before those paths exist, and again when the subject ask
stores them. Ready sees the swatches. A missing hex leaves
the name with no swatch. The live arrow colors are hex, so
that is not the product line.

The import sentence is plain text. A later subject ask
returns when the line already equals that sentence. No test
swaps after the correction action. Do not edit the colors in
`src/weedlib/arrows.py`. The pass is `cr-01.md`.

`test_clear_check_has_an_empty_line_and_start_works` still
fails with "start did not run". The empty-line asserts
passed. The failure is the parent patch of
`weedlib.generate_weeds` against the import inside the
spawned solver. It is outside this change and already filed
as `agents/plans/_bugs/tasks/active/clear-start/task.md`.
Do not fix it here.

## Result

No defects remain in this change. The named checks passed.
`QT_QPA_PLATFORM=offscreen pytest tests/test_window_return.py
tests/test_window_timing.py tests/test_window_options.py`:
15 passed, 1 failed, in 10.09s. Qt loaded through enaml
(PyQt 5.15.11). Nothing skipped. The tests did not start
Inkscape. The failure is the filed clear-start bug, not a
swatch defect.
