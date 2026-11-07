# Ready writer

**Status:** done

## Goal

Correction arrows and their labels go out through one
writer. The host does not classify figures and does not
recompute origins.

## Do

Start after ready-marks. This task calls that result.

`write_correction_svg` in
`extensions/inkscape/weedlines_svg.py` is the only
correction writer. It adds one text element at the label
point, in the arrow color. Do not add a second writer.

The window correction return in
`extensions/inkscape/weedlines_dialog/` uses that writer.
The label point is the one from `build_correction_marks`.
Do not call `classify_figures` on the GUI thread. Do not
classify in the host. Do not recompute origins in the
host.

## Checks

- `tests/test_correction_result.py` and
  `tests/test_window_return.py` pass.
- A present kind gets one text element at that kind's
  origin, in that arrow color, with the label text from
  the marks.
- A kind with no arrows is still omitted.
- The host has no second origin table and no figure
  classification.

## Note

`write_correction_svg` places one text element for each label
from `build_correction_marks`: the mark's text, the mark's
color, and the mark's point. A kind with no arrows is omitted.
Group labels stay `Dangling ends`, `Figure overlaps`, and
`Self-overlaps`. Shafts and heads are unchanged. The writer
does not classify figures and does not compute an origin.

The classify child passes the job records into
`build_correction_marks` and sends each label back. The
correction return, on the GUI thread, gives those labels to
`write_correction_result`, which calls `write_correction_svg`.
The click does not classify and does not start another ask.

Checked with `pytest tests/test_correction_result.py
tests/test_window_return.py tests/test_ready.py`: 12 passed.
A dangling mark is one text element at that origin in
`#FF00FF`, reading `Dangling ends`. An overlap label with no
arrows is absent from the file. The extension does not call
`classify_figures` or `arrow_origin`.

Summary: No defects. One writer places each present kind's
label at the mark's point. The named tests passed.

Context worth keeping: `write_correction_svg` is still the only
correction writer. It does not classify and does not compute an
origin. A kind with no arrows is omitted, including a label that
arrived for that kind. Group labels stay `Dangling ends`,
`Figure overlaps`, and `Self-overlaps`. The text uses the mark's
text, color, and point. Shaft and head `d` values are unchanged.
The classify child calls `build_correction_marks` and sends the
labels. The correction return, on the GUI thread, passes those
stored labels to `write_correction_result`. The host and the
click do not call `classify_figures` or `arrow_origin`. The
solvers, the surround, `weedlines.py`, and the menu were not
edited. The pass is `cr-01.md`.

Result: No defects remain. The named checks passed.
`QT_QPA_PLATFORM=offscreen pytest tests/test_correction_result.py
tests/test_window_return.py tests/test_ready.py`: 12 passed
in 1.26s.

Outside this change: `agents/architecture/host.md`, in Result,
still says a correction result holds only correction arrows.
This writer now also emits one text element per present kind.
That file is human-owned and was not edited.
