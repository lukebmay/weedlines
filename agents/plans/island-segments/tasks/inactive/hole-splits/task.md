# Hole splits

**Status:** done

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

`enclosure_weeds` keeps the splits path from `_hole_internal_splits`
and reports it with `_publish_path_segments` at that add, after
`out.addPath` and before `_drop_parallel_hugs`. The report is the
splits path, not `out`. `_add_line_segs` still does not report.
The path island-hop returns is not published. `_hole_internal_splits`,
`grid_weeds`, `frame_weeds`, `progress.py`, and the window were
not edited.

Why: those splits were drawn with `moveTo` and `lineTo` and never
reached the geometry hook. On a 200 by 160 frame with a 180 by 140
hole at (10, 10), padding 8, collar 4, the hook received nothing.
Reporting `out` or the returned path would report the other
accepted segments again.

The stored ends are the clip refine, about 1.3e-7 short of y=150.
The path is unchanged. The new test allows 1e-6.

Checked with `pytest tests/test_progress.py tests/test_weeds.py`:
152 passed, 4 skipped, 123.08s. No Inkscape. The skips are the
four Inkcut job-pipeline skips in `tests/test_weeds.py`.
`test_hole_splits_reach_the_geometry_hook` skips without
pyclipper; pyclipper is installed, so it ran. The hook receives
`(70, 10)–(70, 150)` and `(130, 10)–(130, 150)` once each, and
has them before `_drop_parallel_hugs`. The path still returns
those two. The island-hop paths locked in `tests/test_weeds.py`
still match. `test_frame_and_grid_check_before_first_segment`
and `test_large_grid_cancel_at_start_raises` passed in that run.
Status left `in-progress`.

## Summary

No defects remain in this change. Hole splits are reported from
the splits path at the add in `enclosure_weeds`, after
`out.addPath` and before `_drop_parallel_hugs`. The hook
receives the two splits once each. The path island-hop returns
is unchanged. Grid and frame were not edited.

## Context worth keeping

The only product edit is in `enclosure_weeds`. `splits` is the
path from `_hole_internal_splits`. `_publish_path_segments(splits)`
reports that path, not `out`, and not the path island-hop
returns. `_add_line_segs` still does not report.
`_hole_internal_splits`, `grid_weeds`, `frame_weeds`,
`progress.py`, and the window were not edited.

On a 200 by 160 frame with a 180 by 140 hole at (10, 10),
padding 8, collar 4, the path returns two segments and the
hook receives those two before `_drop_parallel_hugs`. The
stored y ends are the clip refine, about 149.99999986961484,
1.3e-7 short of 150. The test allows 1e-6. The drawn splits
were not changed. A later pass that drops a split is not
locked by a fixture. The publish is before that pass, so a
drop does not report the split again.

The pass is `cr-01.md`.

Some seals are still reported twice. Not this change. File
`src/weedlib/solvers.py`. Two 30 by 20 rectangles at (0, 0)
and (50, 0), padding 10, collar 4: the path has 19 segments
and the hook receives 21. `(30, 0)–(50, 0)` is reported from
both `_add_seg` calls in `_agglomerate_islands`.
`(30, 20)–(50, 20)` is reported from both `_add_seg` calls
in `_seal_frame_peninsulas`. One call writes the weed path.
The other writes the `seen` copy. The returned path has each
once.

## Result

No defects remain in this change. The named checks passed.
`pytest tests/test_progress.py tests/test_weeds.py` passed
(152 passed, 4 skipped, 123.50s, no Inkscape). The skips are
the four Inkcut job-pipeline skips.
`test_hole_splits_reach_the_geometry_hook` ran.
`test_frame_and_grid_check_before_first_segment` and
`test_large_grid_cancel_at_start_raises` passed in that run.
Status left `in-progress`.
