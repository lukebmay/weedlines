# Ready menu

**Status:** ready

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
two-step above. Do not edit the `solvers.py` sentence in
`algorithms.md`.

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

## Note

The developer writes what changed, why, and how it was checked.
The reviewer then writes the summary, the context worth keeping,
and the result.
