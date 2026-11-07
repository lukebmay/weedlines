# Dialog package

**Status:** ready

## Goal

The window lives in `extensions/inkscape/weedlines_dialog/`.
Geometry stays in the child. No file this task edits is
over 1000 lines.

## Do

The file list is the Dialog section of
[`../../../stages/split.md`](../../../stages/split.md).
These are different files from the library tasks. This
task may run beside them.

Create the package and its README index. Delete
`extensions/inkscape/weedlines_dialog.py` when the
package replaces it. Tests keep importing
`run_weedlines_dialog`, `_spawn_ask`, `_ASK_HOLD`,
`_ASK_TRACE`, and `_burn_hold` from `weedlines_dialog`.

The groups in the stage stay whole: form, run controls
(Start with Pause, Clear All, Apply, and Close), and the
return line. The GUI thread does not call
`classify_figures`, `build_surrounds`, or
`generate_weeds`. Close and Clear All do not join the
child. Work marks stay stored and unpainted. Do not edit
`weedlines.py`.

Split `tests/test_window_surround.py` before editing it,
by the window behaviors it already tests. The other
window tests that import the dialog stay whole.

## Checks

- These pass, including the files split from
  `tests/test_window_surround.py`:
  `tests/test_window_gate.py`,
  `tests/test_window_options.py`,
  `tests/test_window_preview.py`,
  `tests/test_window_return.py`,
  `tests/test_window_surround.py`, and
  `tests/test_window_timing.py`.
- No file this task edits is over 1000 lines.
- `import weedlib` still exposes `__all__`.
- Imports of the dialog names above still come from
  `weedlines_dialog`, including in
  `tests/test_cut_stroke.py`.

## Note

The developer writes what changed, why, and how it was checked.
The reviewer then writes the summary, the context worth keeping,
and the result.
