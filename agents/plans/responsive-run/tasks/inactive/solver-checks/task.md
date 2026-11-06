# Solver checks

**Status:** done

## Goal

Frame, grid, and island-hop call the progress checks
during the work, not only when the mode starts and when
a segment is accepted.

## Do

`src/weedlib/solvers.py`, using the hook from
progress-focus. Keep the phase names island-hop already
reports. Add checks inside frame, grid, and any
island-hop stretch that can run long without accepting a
segment.

`_add_seg` already checks on an accepted segment. Leave
that. A stretch that builds geometry before the first
accepted segment still has to check.

A check may name the one object or the one trial line
the solver is on. Do not change the weed path. Do not
add conquer.

## Checks

`pytest tests/test_weeds.py tests/test_progress.py` with
no Inkscape.

- Frame, grid, and island-hop still return the same weed
  paths on the tests that lock those paths.
- On a keep large enough that grid emits many lines, a
  cancel hook set at the start raises `WeedCancelled`
  before the function returns the finished path.
- A host records a check from frame and from grid before
  the first accepted segment.

## Note

`progress.check` is the hook. `progress.py` was not extended.
`report`, `check_pause`, `check_cancel`, and `report_segment` are
unchanged. `_add_seg` still calls `check_cancel` when a segment
is accepted. Phase names are unchanged. The weed path is unchanged.

Confirmed in `src/weedlib/solvers.py`: before this change, progress
ran from `_add_seg` only after a segment was accepted, and
`debug.phase` checked on enter and exit. Frame published its
rectangle with no `progress.check`. Grid built every hatch line,
then snapped and clearance-tested them, before the first
`check_cancel`. A pocket or seal search inside one phase did the
same until a segment was accepted.

`frame_weeds` now calls `progress.check()` before the rectangle
is accepted. `_grid_in_region` calls it on each vertical and
horizontal trial line before that line is clipped. The same call
names that one line.

The long passes call it on the one trial they are on:
`_seg_body_clearance_ok` before the keep-ring walk,
`_is_parallel_hug` before densify, `_require_connected_ends`
once per segment, `_mouth_seal`'s pair loop before each fuse,
`_iter_bay_far_ends` before each coast trial, and
`_body_pocket_seals` once per bay. A bay names that one body
outline and the mouth line. A seal between two bodies names
the trial line only. A check does not run on every inner
edge comparison.

Why: a 400 square at spacing 5 spends about a second in the
hatch clearance and another in the connected-ends scan, with
no check until the surround rectangle. A 4 by 4 of small
rectangles spends the seal search inside `_mouth_seal`. An
8-tooth comb spends the pocket search in coast trials and
hug tests, tens of seconds, before the bay accepts a segment.
One check per trial lands inside those stretches. A check per
edge comparison would be millions of checks.

Checked with `pytest tests/test_weeds.py tests/test_progress.py`:
151 passed, 4 skipped, 124.91s. No Inkscape. The skips are the
existing Inkcut job-pipeline skips. Frame, grid, and island-hop paths still
match. A 400 square grid with cancel true at the start raises
`WeedCancelled` and returns no path. Frame records a check
before its first segment. Grid records more than one named
line before its first segment. A 2 by 2 seal search records
line checks while emits are still going, and cancel from that
search raises. A U-shaped keep records a pocket check that
names one outline and one mouth. With no hooks, `check`
returns and the path tests still match. Surround, figures,
and the window were not edited. Status left `in-progress`.

## Summary

No defects remain. Frame, grid, and island-hop call `progress.check`
during the work, not only when a phase starts and when a segment
is accepted. A check names one outline, one trial line, or neither.
The name is not a cut. The weed path is unchanged. A cancel raises
`WeedCancelled` and returns no path. On the keeps that run long,
the longest gap between pause and cancel checks is about 0.21s.

## Context worth keeping

`progress.check` is the hook. `progress.py` was not extended.
`report`, `check_pause`, `check_cancel`, and `report_segment` are
unchanged. `_add_seg` still calls `check_cancel` when a segment
is accepted. Phase names are unchanged.

Frame checks once, before the rectangle is accepted. Grid names
each hatch line before it is clipped. Clearance, parallel-hug,
and the connected-ends scan each check once per trial segment.
A seal between two bodies names only that trial line. A pocket
names the one body outline and the mouth, then each coast trial.
A check does not run on every edge comparison.

A 400 square at spacing 5 is about 1.4s, longest gap about 0.03s.
A 4 by 4 of small rectangles is about 15s, longest gap about
0.09s. An 8-tooth comb is about 11s, longest gap about 0.04s.
The quoted frame with holes, the slowest keep in the weed tests,
is about 15s, longest gap about 0.21s, in the mouth-seal setup
before the next trial line. With no hooks, `check` returns and
the segments match. The pass is `cr-01.md`.

Grid hatch lines still reach the geometry hook only from
`_publish_path_segments` after the connected-ends pass, and a
work-rect side that is not already a hatch line is sent again
there. File `src/weedlib/solvers.py`. On an 80 by 60 keep,
padding 2, spacing 20, `(82, -2, 82, 62)` and
`(82, 62, -2, 62)` are each delivered twice. This change did
not cause that. It is not a remedy for this unit.

## Result

No defects remain. The named checks passed.
`pytest tests/test_weeds.py tests/test_progress.py` passed
(151 passed, 4 skipped, 125.16s, no Inkscape). The skips are
the existing Inkcut job-pipeline skips.
