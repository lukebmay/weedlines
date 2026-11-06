# Hole splits

**Status:** ready

## Goal

A hole split island-hop accepts reaches the geometry hook
then. The path the mode returns stays the same.

## Do

`src/weedlib/solvers.py`, at the hole-split add in
`enclosure_weeds` only. Add the check in
`tests/test_progress.py`.

`enclosure_weeds` adds `_hole_internal_splits` with
`out.addPath`. Those splits are drawn by `_add_line_segs`,
which only calls `moveTo` and `lineTo`. Report each segment
of that splits path at the add, before
`_drop_parallel_hugs`. Report the splits path, not `out`.
`_add_seg` already reports the other accepted segments.

Do not report from inside `_add_line_segs`. `grid_weeds`
and `_clip_path_to_waste` use it, and grid already reports
hatch. Do not publish the path island-hop returns. That
would report the other segments again.

A split reported at the add stays reported once even if a
later pass drops or shortens it. Do not change the splits
`_hole_internal_splits` draws.

Do not change `grid_weeds`, `frame_weeds`, the progress
checks, or `src/weedlib/progress.py`. Do not edit the
window.

## Checks

`pytest tests/test_progress.py tests/test_weeds.py`. No
Inkscape. The new test skips without pyclipper.

- Outer rect 200 by 160, hole 180 by 140 centered at
  (10, 10), padding 8, collar 4. `island_hop_weeds` still
  returns two segments, `(70, 10)–(70, 150)` and
  `(130, 10)–(130, 150)`.
- The geometry hook receives those two, each once, and no
  others. It has them before `_drop_parallel_hugs` runs.
- The island-hop paths locked in `tests/test_weeds.py`
  still match.
- Grid still reports hatch before connected-ends, and each
  work-rectangle edge once. Frame still publishes its
  rectangle once.
- `test_frame_and_grid_check_before_first_segment` and
  `test_large_grid_cancel_at_start_raises` still pass.

## Note

The developer writes what changed, why, and how it was checked.
The reviewer then writes the summary, the context worth keeping,
and the result.
