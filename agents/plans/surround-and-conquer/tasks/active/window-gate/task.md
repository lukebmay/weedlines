# Window gate

**Status:** ready

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

The developer writes what changed, why, and how it was checked.
The reviewer then writes the summary, the context worth keeping,
and the result.
