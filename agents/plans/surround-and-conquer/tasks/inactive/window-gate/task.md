# Window gate

**Status:** done

## Goal

Frame, grid, and island-hop start only when the figure check is
clear. The solver keep path for that run is the subject region.
No control starts a cut while a defect is reported.

## Do

- In `extensions/inkscape/weedlines_host.py` and the inline path in
  `extensions/inkscape/weedlines.py`, pass the job's path records
  into the window, not the union. Also pass document width, height,
  and viewBox. Keep the detached spawn and the inline path.
- In `extensions/inkscape/weedlines_dialog.py`, ask
  `classify_figures` and the region call. Do not reimplement
  topology. Pass the subject region to `generate_weeds` as keep.
- Start stays disabled while the check reports a defect. No other
  control starts a mode. The mode list stays frame, grid, and
  island-hop. Do not add Surround and Conquer, and do not edit
  `extensions/inkscape/weedlines.inx`.
- Do not edit `src/weedlib/solvers.py`. Do not add the correction
  line or the color controls.
- A weed-line Apply still returns cuts to the host, which still
  writes today's result.
- Tests go in `tests/test_window_gate.py`. Run them offscreen
  (`QT_QPA_PLATFORM=offscreen`) when Qt loads. Skip when Qt cannot
  load. No Inkscape.

## Checks

- A defect disables Start. A clear design enables Start for frame,
  grid, and island-hop.
- The path passed into `generate_weeds` is the subject region. A
  clear filled rectangle still cuts in those three modes.
  Island-hop may skip when pyclipper is missing, as
  `tests/test_weeds.py` already does.
- `pytest tests/test_weeds.py tests/test_window_gate.py` passes
  aside from that skip. `src/weedlib/solvers.py` is unchanged.
- The mode list has no Surround and Conquer entry.

## Note

The window starts from the job's per-path records. The detached host
and the inline path both pass those records, plus document width,
height, and viewBox. They do not pass the keep union.
`classify_figures` then `subject_weed_regions(..., swap=False)` run
in the dialog. Start stays disabled while that check has a defect,
and no other control calls `generate_weeds`. The keep path for a
start is the subject region. Apply still returns the cuts. The host
still writes today's result through `write_result` (`keep_d` and
`doc_attrs` unchanged). The detached spawn is unchanged. The mode
list is still frame, grid, and island-hop.

The extension still aborts when the selection has no path geometry.
The detached process no longer refuses a job whose keep union is
empty; it opens on the records.

Checked with `QT_QPA_PLATFORM=offscreen pytest tests/test_weeds.py
tests/test_window_gate.py`: 147 passed, 4 skipped. Those skips are
the existing Inkcut job-pipeline skips in `tests/test_weeds.py`.
Island-hop ran (pyclipper is installed). The rectangle cut uses
padding 2 and spacing 20, the same values as
`test_generate_weeds_modes`, because that is a clear rectangle the
three modes already cut. `src/weedlib/solvers.py`,
`extensions/inkscape/weedlines.inx`, and `write_result` were not
edited.

Review summary: no defects remain. The change matches the task.
The detached host and the inline path pass per-path records, plus
document width, height, and viewBox, and they do not pass the keep
union. The dialog asks `classify_figures` and
`subject_weed_regions(figures, swap=False)`. Start stays disabled
while that check has a defect, and only Start calls
`generate_weeds`. The keep path is the subject region. The mode
list is frame, grid, and island-hop. Apply still returns the cuts.
The host still writes today's result through `write_result`.

Context worth keeping: `blocked` is `bool(check.defects)`, so
every defect kind disables Start. The test uses an open path.
`swap` stays false, so the keep path is the unswapped subject.
Document width, height, and viewBox are stored on the dialog as
`doc_width`, `doc_height`, and `doc_viewbox`. They are not used to
cut. `keep_d` is still the union written with
`close_subpaths=True`, and it is only the result's design copy.
The extension still aborts when the selection has no path
geometry. The detached host no longer returns on an empty keep
union; the host test does not use an empty `keep_d`. No
correction line and no color controls. The pass is `cr-01.md`.

Result: no defects remain. The named checks passed.
`QT_QPA_PLATFORM=offscreen pytest tests/test_weeds.py
tests/test_window_gate.py` passed (147 passed, 4 skipped). The
skips are the Inkcut job-pipeline skips in `tests/test_weeds.py`.
Island-hop ran. Qt loaded. The new tests do not load Inkscape.
`src/weedlib/solvers.py` has no test; its diff is empty.
`extensions/inkscape/weedlines.inx` is unchanged.
