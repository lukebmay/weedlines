# Figure checks

**Status:** done

## Goal

The figure check calls the progress checks while it
classifies, so a long check can pause, clear, and name
what it is testing.

## Do

`src/weedlib/figures.py`, using the hook from
progress-focus. Call it during the defect passes, not
only when the result is about to return. A check may
name the one figure outline under test. Do not name a
candidate line unless the check is actually trying one.

Do not change which defects are reported. A host with no
hooks still gets the same result. Do not edit the
surround or the solvers.

## Checks

`pytest tests/test_figures.py tests/test_progress.py`
with no Inkscape. Skip when Qt cannot load.

- The curved-hole cases and the other figure tests keep
  their results.
- A cancel hook set at the start of a check that walks
  more than one figure raises `WeedCancelled` before the
  result returns.
- A host records a check before that return.

## Note

`_one_point_per_region` calls a nameless `progress.check()` in the
three loops after `_crossing_regions` returns. Once per polygon
point, before the chords to later points. Once per point against
one region, before `_meets_region`. Once per region pair, before
`_sample_sets_meet`. Those calls name neither figure and no line.
They are not in `_segment_in_both` or `_piece_hits`.
`WeedCancelled` is not caught. The twin walk, the self-overlap
piece walk, the overlap pair, and the mark walk still check where
the first pass put them. `progress.py` was not extended. Which
defects are reported is unchanged.

Why: those three loops are the merge after the mark walk. A check
only before that merge leaves Pause and Clear All waiting on the
region comparisons. On three disjoint ellipse pairs that stretch
is about a second. On four pairs it is longer.

Checked with `pytest tests/test_figures.py tests/test_progress.py`:
53 passed, 14.80s. No Inkscape. Qt loaded, so nothing skipped.
`test_region_merge_checks_while_a_comparison_remains` sees a
nameless check while a later region comparison is still waiting.
A cancel from that window raises `WeedCancelled` and returns no
result. The two-lens case still reports two overlaps. Solvers,
the surround, and the window were not edited. Status left
`in-progress`.

## Summary

No defects remain. The twin walk, the self-overlap piece walk, the overlap pair, and the mark walk call `progress.check`. The merge after the mark walk checks once per polygon point, once per point against one region, and once per region pair. Those checks name neither figure and no line. The reported defects do not change. On three 2.5 ellipses shifted by 1.2, the longest gap between checks is about 0.13s.

## Context worth keeping

`progress.check` is the hook. It was not extended. A missing name clears that mark. The host gets a copy. The geometry hook is not called. A call names one outline, or neither, and never a line.

`_without_twins` checks once per subpath and names that subpath. `_self_overlap_defects` checks once per border piece and names that piece's subpath. `_overlap_defects` checks once per pair and names neither figure. `_linked_mark_groups` checks once per mark and names that one border. A check on every chord inside one comparison is not required, and it is not in `_segment_in_both` or `_piece_hits`.

`_one_point_per_region` calls a nameless `progress.check()` after `_crossing_regions` returns. Once per polygon point, before the chords to later points. Once per point against one region, before `_meets_region`. Once per region pair, before `_sample_sets_meet`. `WeedCancelled` is not caught. On three `addEllipse` copies of size 2.5, centers 3 apart, against the same set shifted by 1.2, one region comparison is about 0.13s. Four copies reach about 0.18s. Six reach about 0.26s. The 96-side ring's point loop, 36 polygon points, has a longest gap of about 24ms. An 800-segment self-overlap stayed under about 2ms. An 8 by 8 of overlapping squares stayed under about 6ms.

A cubic is named by its endpoints. An ellipse name is one subpath. That is not a defect.

No bug outside this change. The pass is `cr-02.md`.

## Result

No defects remain. The merge checks while a later region comparison is still waiting, and a cancel from that check raises `WeedCancelled` with no result.
`pytest tests/test_figures.py tests/test_progress.py` passed (53 passed, 14.74s, no Inkscape).
