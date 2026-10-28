# Window return

**Status:** ready

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

The developer writes what changed, why, and how it was checked.
The reviewer then writes the summary, the context worth keeping,
and the result.
