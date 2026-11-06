# Extension doc

**Status:** ready

## Goal

`docs/inkscape-extension.md` stops saying the dialog opens
on Start Algorithm / Cancel.

## Do

Edit only `docs/inkscape-extension.md`.

The install step that says a custom dialog opens with
**Start Algorithm** / **Cancel…** names Start, Pause, Clear
All, Apply, and Close instead. Leave the rest of that
paragraph, including the log, the preview, and the
following Apply sentence. Do not rewrite the install
steps.

Do not edit the units section. surround-doc spinner-labels
owns those sentences. Do not edit the window or the
solvers. Do not invent conquer. Do not remove island-hop
if this file names it.

## Checks

- The file does not say "Start Algorithm" or offer Cancel
  as a control.
- That dialog sentence names Start, Pause, Clear All,
  Apply, and Close.
- The units section is unchanged by this task.
- `docs/inkscape-extension.md` is the only changed file.
- No product test reads this file.

## Note

The developer writes what changed, why, and how it was checked.
The reviewer then writes the summary, the context worth keeping,
and the result.
