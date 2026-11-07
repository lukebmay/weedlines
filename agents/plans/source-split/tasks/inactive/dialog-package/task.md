# Dialog package

**Status:** done

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

`extensions/inkscape/weedlines_dialog.py` is now the package
`extensions/inkscape/weedlines_dialog/`. `__init__.py` builds the
window and returns the Apply path, the layer name, and the weed-line
color. The stage modules are `geometry_ask.py`, `inbox.py`,
`preview.py`, `run_controls.py`, `form.py`, and `return_line.py`.
The README names each file in one sentence. The nested closure is
one window object. Method bodies match the old functions. Geometry
calls stay in the child. Close and Clear All do not join it. Work
marks stay stored and unpainted. Progress is still installed in the
child for every ask. Tests still import `run_weedlines_dialog`,
`_spawn_ask`, `_ASK_HOLD`, `_ASK_TRACE`, and `_burn_hold` from
`weedlines_dialog`. Those three patched names are read from the
package on each ask.

A package cannot also be `weedlines_dialog.py`, so that file is
gone. `weedlines.inx` and `WEED_FILES` name the package modules.
The installer creates the destination directory before it links a
nested path. `import weedlines_dialog` still resolves. `weedlines.py`
was not edited.

`tests/test_window_surround.py` was split by the behaviors it
already tested: preview and start stay in that file, the run is
`tests/test_window_surround_run.py`, and display units are
`tests/test_window_units.py`. Assertions were moved, not rewritten.
The other window tests stayed whole.

Checked: `pytest` on `tests/test_window_gate.py`,
`tests/test_window_options.py`, `tests/test_window_preview.py`,
`tests/test_window_return.py`, `tests/test_window_surround.py`,
`tests/test_window_surround_run.py`, `tests/test_window_units.py`,
`tests/test_window_timing.py`, and `tests/test_cut_stroke.py` —
85 passed. New modules are 154 to 754 lines. `import weedlib` still
exposes `__all__`. `src/weedlib/` and the surround package were not
edited.

Summary: No defects. The dialog package keeps the old window
behavior. Geometry stays in the child. The named tests passed.

Context worth keeping: `__init__.py` builds the widgets.
`form.py` is the options behavior. `run_controls.py` holds
Start with Pause, Clear All, Apply, and Close. `return_line.py`
holds the defect line and both return actions. `classify_figures`,
`build_surrounds`, and `generate_weeds` run only in the child.
Close and Clear All do not join it. Progress is installed for
classify and surround, not only the solver. Focus marks are
stored and not painted. `_ASK_HOLD`, `_ASK_TRACE`, and
`_spawn_ask` are read from the package on each ask. There is
no `weedlines_dialog.py` beside the package. `weedlines.inx`
and `WEED_FILES` name the package modules, and the installer
creates the parent directory before a nested link. The surround
window tests moved unchanged into preview and start, the run,
and display units. `weedlines.py` and `src/weedlib/` were not
edited. The pass is `cr-01.md`.

Result: No defects remain. The named checks passed.
`QT_QPA_PLATFORM=offscreen pytest` on the nine window files:
85 passed in 21.65s. No bug outside this change.
