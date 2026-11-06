# Seal report

**Status:** done

## Goal

Each island-hop seal is reported once. The path the mode
returns stays the same. If the double report cannot be
confirmed, the task closes with no code change.

## Do

A reviewer reported this. Confirm it before changing code.
Two 30 by 20 rectangles at (0, 0) and (50, 0), padding 10,
collar 4. The report says the path has 19 segments and the
hook receives 21. `(30, 0)–(50, 0)` comes from both
`_add_seg` calls in `_agglomerate_islands`.
`(30, 20)–(50, 20)` comes from both `_add_seg` calls in
`_seal_frame_peninsulas`. One call writes the weed path.
The other writes the `seen` copy. The returned path has
each once.

If that case does not report a segment twice, stop. Say
what the hook received. Do not change code.

If it does, report each of those seals once. Do not change
the path island-hop returns. Do not report from inside
`_add_line_segs`. Do not change the hole-split report,
`grid_weeds`, or `frame_weeds`. Do not edit the window or
`src/weedlib/progress.py`.

## Checks

`pytest tests/test_progress.py tests/test_weeds.py` with
no Inkscape.

- On that two-rectangle case, the hook receives each seal
  once, and the returned path is unchanged.
- The hole-split check still receives its two splits once.
- The island-hop paths locked in `tests/test_weeds.py`
  still match.

## Note

Confirmed before the edit. Two 30 by 20 rectangles at (0, 0) and
(50, 0), padding 10, collar 4: `island_hop_weeds` returned 19
segments and the geometry hook received 21. `(30, 0)–(50, 0)`
came from both `_add_seg` calls in `_agglomerate_islands`.
`(30, 20)–(50, 20)` came from both `_add_seg` calls in
`_seal_frame_peninsulas`. One call writes the weed path. The
other writes the `seen` copy. The returned path had each once.

`_add_seg` now takes `report=True`. The `seen` copy in every
island-hop seal pass passes `report=False`: agglomerate,
divergent corridors, compact ties, frame peninsulas, hanging
gutters, bay seals, and body pockets. The weed-path call still
reports. The gates and the drawn segments are unchanged.
`_add_line_segs` still does not report. The hole-split publish,
`grid_weeds`, `frame_weeds`, `progress.py`, and the window were
not edited.

Why: `_add_seg` reports every accept. The `seen` path is the
same seal recorded so a later pass does not cut it again, not
a second cut. Leaving the other passes on the old pair would
report the next seal twice the same way.

Checked with `pytest tests/test_progress.py tests/test_weeds.py`:
153 passed, 4 skipped, 123.81s. No Inkscape. `QT_QPA_PLATFORM`
was `offscreen`. The skips are the four Inkcut job-pipeline
skips in `tests/test_weeds.py`.
`test_island_hop_seals_reported_once` ran. On that case the
path is still the same 19 segments, and the hook receives
those 19, including `(30, 0)–(50, 0)` and `(30, 20)–(50, 20)`
once each. `test_hole_splits_reach_the_geometry_hook` passed
in that run. The island-hop paths locked in `tests/test_weeds.py`
still match.
Status left `in-progress`.

## Summary

No defects remain in this change. Each island-hop seal is
reported once. The path island-hop returns is unchanged.
The hole-split report, grid, and frame were not edited.

## Context worth keeping

`_add_seg` takes `report=True`. The flag is checked after
the gates, the write, the accept log, and the cancel check.
Only `report_segment` is skipped when it is false. The
`seen` copy in every island-hop seal pass that writes the
same segment twice passes `report=False`: agglomerate,
divergent corridors, compact ties, frame peninsulas,
hanging gutters, bay seals, and body pockets. The weed-path
call still reports. Compact ties still write `seen` first.
`_add_line_segs` still does not report. The hole-split
publish is still `_publish_path_segments(splits)`.
`grid_weeds`, `frame_weeds`, `progress.py`, and the window
were not edited.

On two 30 by 20 rectangles at (0, 0) and (50, 0), padding
10, collar 4, the path is still 19 segments. The hook
receives those 19, including `(30, 0)–(50, 0)` and
`(30, 20)–(50, 20)` once each. The other six passes use the
same `seen` flag. This fixture does not draw them.

The pass is `cr-01.md`.

## Result

No defects remain in this change. The named checks passed.
`pytest tests/test_progress.py tests/test_weeds.py` passed
(153 passed, 4 skipped, 123.37s, no Inkscape). `QT_QPA_PLATFORM`
was `offscreen`. The skips are the four Inkcut job-pipeline
skips in `tests/test_weeds.py`.
