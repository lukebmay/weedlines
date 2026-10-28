# Window return

**Status:** done

## Goal

A defect shows a line and two actions under the preview. The
arrow action writes the correction result and does not open a
message box.

## Do

- Edit `extensions/inkscape/weedlines_dialog.py` only. Do not edit
  `extensions/inkscape/weedlines_host.py`. The host's Apply notice
  stays the weed-line notice.
- The line, the action labels, and when the second action is
  present are Return actions in `agents/architecture/preview.md`.
  They sit in the layout under the preview pane. They are not a
  message box, a popover, or any other surface over the preview.
- "Return to Inkscape" writes no result and closes the window.
- "Return to Inkscape with correction arrows" writes the correction
  result, using the same arrow paths as the preview, then replaces
  the line with the import sentence in that part. It does not close
  the window.
- When the check is clear, the line is empty, the correction
  action is absent, and Start works.
- Tests go in `tests/test_window_return.py`. Offscreen when Qt
  loads. No Inkscape.

## Checks

- With a defect, the line and both actions are under the preview.
  The second action is absent when there is no defect.
- The plain return writes no result file and closes. The arrow
  return writes a correction result, leaves the window open, and
  does not open a message box.
- The written paths are the preview arrow paths. Start stays
  disabled while a defect exists.
- `pytest tests/test_window_return.py tests/test_correction_result.py`
  passes without Inkscape. The window test skips only when Qt is
  missing.

## Note

The return line and its actions are in the dialog layout, directly
under the preview splitter. They are ordinary widgets, not a message
box. With a defect the line names each kind that is present, and
both actions are shown. "Return to Inkscape" rejects the dialog and
writes nothing. "Return to Inkscape with correction arrows" calls
`write_correction_result` with the arrow batches `refresh_preview`
already painted from `build_arrow_paths`, then replaces the line
with the import sentence and leaves the window open. The document
width, height, and viewBox go along as `doc_attrs`. When the check
is clear the line is empty, the correction action is not created,
and Start still runs. The host file was not edited, so the Apply
notice stays the weed-line notice.

Checked with `QT_QPA_PLATFORM=offscreen pytest
tests/test_window_return.py tests/test_correction_result.py`: 9
passed. Qt loaded. Those tests do not start Inkscape. The same
offscreen command for `tests/test_window_preview.py` and
`tests/test_window_gate.py` passed (15 passed) after the layout
change.

Review summary: no defects remain. The line and both actions are
ordinary widgets under the preview, not a message box. Plain
return rejects and writes nothing. Arrow return writes the
preview batches from `build_arrow_paths`, replaces the line with
the import sentence, and leaves the window open. Start stays
disabled while a defect exists. On a clear check the line is
empty, the correction action is absent, and Start runs. The host
file was not edited.

Context worth keeping: the row is the next layout after the
preview splitter. `blocked` is `bool(check.defects)` and does not
change. Start is enabled only when the window is idle and the
check is clear. The arrow action stores no second path set. It
writes `state['arrows']` and does not accept or reject. A return
therefore does not reach the host's Apply notice. When the check
is clear, "Return to Inkscape" stays. The guide asks for an empty
line and no correction action. An offscreen probe showed the
three widgets inside a 720 by 859 dialog, below the preview. The
pass is `cr-01.md`.

Result: no defects remain. The named checks passed.
`QT_QPA_PLATFORM=offscreen pytest tests/test_window_return.py
tests/test_correction_result.py tests/test_window_preview.py
tests/test_window_gate.py` passed (24 passed, no skips). Qt
loaded. The tests do not start Inkscape. The window test skips
only when Qt cannot load. That skip did not run. `git diff
--exit-code -- extensions/inkscape/weedlines_host.py` is empty.
