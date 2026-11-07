# Ready menu

**Status:** done

## Goal

Make ready to cut returns at once. Reimport last ready
places the ready file. The open document is not changed
by the check.

## Do

Start after ready-writer. The writer already draws the
labels. Do not write cleanup behavior. The cleanup stage
has no tasks.

Menu names, character for character:

- `Auto generate weedlines…`
- `Make ready to cut`
- `Reimport last ready`
- `Reimport last weedlines`

The ellipsis is only on `Auto generate weedlines…`.
Reimport is one word. Inkscape sorts the menu
alphabetically. Do not add a divider and do not add a
sort prefix.

`Make ready to cut` spawns the check and returns at
once. Detach the child so the return does not kill it.
The effect does not change the open document. The child
calls `build_correction_marks` and writes the ready file
through `write_correction_svg` only when there is a
defect. A clear check writes none and removes a stale
ready file. The ready file is not the weed-line result.

`Reimport last ready` places that file: one layer,
`Weedlines corrections`, the groups, the labels, above
the design, no design copy, no message box. `Reimport
last weedlines` still places a weed-line result and
refuses a ready file.

The window hint names `Reimport last ready`.

Update the menu sentences in
`agents/architecture/host.md` in this task. The user
named these entries. The behavior sentence is the
two-step above. The correction-result sentences also
say a present kind has one text label at the kind
origin, in the arrow color. They no longer say the
result holds only arrows. Do not edit the `solvers.py`
sentence in `algorithms.md`.

## Checks

- The effect returns without waiting on the check, and
  Inkscape is not asked to apply a document change from
  that effect.
- A defect writes one ready result through
  `write_correction_svg`. A clear check removes a stale
  ready file and does not write one.
- Reimport last ready places one corrections layer above
  the design, with the groups and labels, and no design
  copy and no message box.
- Reimport last weedlines places a weed-line result and
  refuses a ready file.
- The four menu names match the list above.
- `tests/test_window_return.py` and
  `tests/test_cut_stroke.py` pass with the new hint.
- `host.md` names the four entries and the two-step.
  It does not say the correction result holds only arrows.

## Note

The Weedlines menu names are `Auto generate weedlines…`,
`Make ready to cut`, `Reimport last ready`, and
`Reimport last weedlines`. The ellipsis is only on the
first. There is no divider and no sort prefix.

`Make ready to cut` writes a job and detaches
`weedlines_ready.py`. The effect returns false and
`has_changed` stays false, so this Inkscape is not asked
to apply the document. The child calls
`build_correction_marks`. A defect writes `last_ready.svg`
through `write_correction_svg`. A clear check removes that
file and does not write one. The file is not
`last_result.svg`.

`Reimport last ready` places that file with the existing
correction import: one `Weedlines corrections` layer, the
groups, and the text label, above the design. `Reimport
last weedlines` still places a weed-line result and refuses
a ready file. The window hint and the correction return
name `Reimport last ready`. The installer lists
`weedlines_ready.py`, `weedlines_ready.inx`, and
`weedlines_reimport_ready.inx`.

`host.md` names the four entries, the two-step, and the
text label at the kind origin in the arrow color.

Checked with `pytest tests/test_ready_menu.py
tests/test_correction_import.py tests/test_window_return.py
tests/test_cut_stroke.py`: 27 passed.

Summary: One defect. Make ready returns at once and writes
`last_ready.svg` only when the check has a defect. The
correction return still writes `last_result.svg`, then names
`Reimport last ready`, which reads the other file.
`Reimport last weedlines` refuses that correction-shaped
result. Neither menu places those arrows.

Context worth keeping: `spawn_detached` starts a new session
and does not wait. The effect returns false and `has_changed`
stays false. The child calls `build_correction_marks` and
`write_correction_svg`. A clear check deletes `last_ready.svg`.
That file is not `last_result.svg`. `Reimport last ready`
places one `Weedlines corrections` layer above the design,
with the groups and the label, and no design copy. The four
menu names match, with the ellipsis only on `Auto generate
weedlines…`. `host.md` names the entries, the two-step, and
the text label. It does not say the result holds only arrows.
The `solvers.py` sentence in `algorithms.md` was not edited.
There is no second writer, no auto-correct, and no
convert-to-path. The installer lists `weedlines_ready.py`,
`weedlines_ready.inx`, and `weedlines_reimport_ready.inx`.
The pass is `cr-01.md`.

Result: One defect remains. Write the correction return to
`last_ready.svg` through `write_correction_svg`. Leave
`last_result.svg` for a weed-line result, and do not refuse
that result by the correction shape while it is the window's
only copy. `QT_QPA_PLATFORM=offscreen pytest
tests/test_ready_menu.py tests/test_correction_import.py
tests/test_window_return.py tests/test_cut_stroke.py`: 27
passed in 2.03s.

Outside this change: `agents/architecture/preview.md` still
says the correction return uses Import last result. The menu
name is `Reimport last ready`. `agents/architecture/runtime.md`
still says that after Apply the person runs Import last
result. The menu name is `Reimport last weedlines`. Neither
file was edited here.

The correction return writes `last_ready.svg` through
`write_correction_svg`. `last_result.svg` stays the weed-line
file. The file that return writes is the one `Reimport last
ready` places. `Reimport last weedlines` still refuses that
correction-shaped result.

Checked with `QT_QPA_PLATFORM=offscreen pytest
tests/test_ready_menu.py tests/test_correction_import.py
tests/test_window_return.py tests/test_cut_stroke.py`: 27
passed in 2.04s.

Summary: No defects. The correction return writes
`last_ready.svg` through `write_correction_svg`. `Reimport
last ready` places that file. `Reimport last weedlines`
still refuses those bytes. A weed-line result still uses
`last_result.svg`.

Context worth keeping: `write_correction_result` passes
`ready_svg_file()` to `write_correction_svg` and does not
create `last_result.svg`. `write_result` still writes
`last_result.svg`. The arrow-return test places the written
ready file and then checks that those bytes are refused on
the weed-line menu. The pass is `cr-02.md`.

Result: No defects remain. The named checks passed.
`QT_QPA_PLATFORM=offscreen pytest tests/test_ready_menu.py
tests/test_correction_import.py tests/test_window_return.py
tests/test_cut_stroke.py`: 27 passed in 2.01s.

Outside this change, already filed: `preview.md` still says
Import last result for the correction return. `runtime.md`
still says Import last result after Apply. The menu names
are `Reimport last ready` and `Reimport last weedlines`.
