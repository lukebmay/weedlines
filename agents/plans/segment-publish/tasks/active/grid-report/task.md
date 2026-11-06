# Grid report

**Status:** done

## Goal

A grid run reports each hatch segment when it is accepted,
before the connected-ends pass. Each work-rectangle edge is
reported once. Publishing the finished path does not report
those segments again.

## Do

`src/weedlib/solvers.py`, in `grid_weeds` only.

Hatch is added through `_add_line_segs`, which does not call
`report_segment`. Report each of those segments at that add,
before `_require_connected_ends` runs. Do not add the report
inside `_add_line_segs`. Island-hop uses it too, and this
stage does not change island-hop.

The work rectangle is added through `_add_path_segs` and
`_add_seg`, which already reports each accepted edge. After
connected-ends and the clip, `_publish_path_segments(weed)`
reports every remaining segment, hatch included, and the
rectangle edges again. Stop that second report. Leave
`frame_weeds` on `_publish_path_segments`. That is frame's
only report.

Connected-ends and the clip still run, and the path
`grid_weeds` returns stays the same. A segment reported at
accept stays reported once even if a later pass drops or
shortens it. Do not report the finished path.

Do not change the progress checks, `src/weedlib/progress.py`,
the weed path, or the display unit. Do not edit the window.
The window already paints a segment the hook reports.

## Checks

`pytest tests/test_progress.py tests/test_weeds.py` with no
Inkscape.

- A grid run reports each accepted hatch segment before
  `_require_connected_ends` is called.
- Each work-rectangle edge is reported once.
- The same segment is not reported again when `grid_weeds`
  returns.
- The grid paths locked in `tests/test_weeds.py` still match.
- `test_frame_and_grid_check_before_first_segment` and
  `test_large_grid_cancel_at_start_raises` still pass.
- Frame still reports its rectangle once.

## Note

`grid_weeds` reports hatch when `_grid_in_region` returns, through
`_publish_path_segments`, before the work rectangle is added and
before `_require_connected_ends`. The rectangle still goes through
`_add_path_segs` and `_add_seg`, which reports each accepted edge.
The finished path is not reported. Connected-ends and the clip
still run, and the path returned is unchanged. `_add_line_segs`,
`frame_weeds`, `progress.py`, and island-hop were not edited.
Frame still publishes its rectangle once.

Why: hatch waited for the connected-ends pass, and a work-rect
edge `_add_seg` had already accepted was reported again with the
finished path. On an 80 by 60 keep, padding 2, spacing 20,
`(82, -2, 82, 62)` and `(82, 62, -2, 62)` are now each delivered
once. A segment reported at accept stays reported once if a later
pass drops it. A letter O, padding 8, spacing 10, reports 34
segments before connected-ends and returns 18. The 16 dropped
segments are not reported again.

Checked with `pytest tests/test_progress.py tests/test_weeds.py`:
151 passed, 4 skipped, 124.26s. No Inkscape. The skips are the
four Inkcut job-pipeline skips in `tests/test_weeds.py`.
`test_frame_and_grid_check_before_first_segment` and
`test_large_grid_cancel_at_start_raises` passed in that run.
The grid paths locked in `tests/test_weeds.py` still match.
Status left `in-progress`.

Island-hop hole splits still never reach the geometry hook.
Not this task. File `src/weedlib/solvers.py`:
`_hole_internal_splits` is added with `out.addPath`. On a
200 by 160 frame with a 180 by 140 hole, padding 8, collar 4,
the returned path has 2 segments and the hook receives 0.

## Summary

No defects remain. Grid hatch is reported when `_grid_in_region`
returns, before the work rectangle and before connected-ends.
Each work-rectangle edge is reported once. The finished path is
not reported. A segment a later pass drops stays reported once.
The path `grid_weeds` returns is unchanged. Frame still reports
its rectangle once. Island-hop was not edited.

## Context worth keeping

The only edit in `src/weedlib/solvers.py` is in `grid_weeds`.
`_publish_path_segments(weed)` runs on the hatch path as soon as
`_grid_in_region` returns. The work rectangle still goes through
`_add_path_segs` and `_add_seg`. The publish after
`_clip_path_to_rect` is gone. `_add_line_segs`, `frame_weeds`,
`progress.py`, and island-hop were not edited.

On an 80 by 60 keep, padding 2, spacing 20, the hook receives
18 segments, each once, and the path returns those 18. Sixteen
are hatch. `(82, -2, 82, 62)` and `(82, 62, -2, 62)` are not
hatch; `_add_seg` reports each once. `(-2, -2, 82, -2)` and
`(-2, -2, -2, 62)` are hatch, so the rectangle copy is
redundant and is not reported again. Nothing is reported after
connected-ends.

A letter O, padding 8, spacing 10, reports 30 hatch segments
and then 4 rectangle edges, 34 before connected-ends, and
returns 18. The 18 are 18 of the 34, with the same coordinates.
The other 16 are not reported again. No segment is reported
twice.

The returned segments match the old call order on that keep, a
40 square, the letter O, and an inner 40 square. A geometry
hook does not change the path. Frame publishes four edges,
each once.

These once-only checks have no test.
`test_frame_and_grid_report_preview_segments` only checks that
frame reports at least four segments and that grid reports
more. The pass is `cr-01.md`.

Island-hop hole splits still never reach the geometry hook.
This diff did not cause that. Not a remedy for this unit.
File `src/weedlib/solvers.py`: `_hole_internal_splits` is added
with `out.addPath`. On a 200 by 160 frame with a 180 by 140
hole, padding 8, collar 4, the path has 2 segments and the
hook receives 0. Those 2 are the splits.

## Result

No defects remain. The named checks passed.
`pytest tests/test_progress.py tests/test_weeds.py` passed
(151 passed, 4 skipped, 123.89s, no Inkscape). The skips are
the four Inkcut job-pipeline skips.
`test_frame_and_grid_check_before_first_segment` and
`test_large_grid_cancel_at_start_raises` passed in that run.
Status left `in-progress`.
