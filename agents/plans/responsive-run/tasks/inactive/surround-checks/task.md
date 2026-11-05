# Surround checks

**Status:** done

## Goal

The surround calls the progress checks during the build,
so pause, clear, and a focus name can happen before the
outline is finished.

## Do

`src/weedlib/surround.py`, using the hook from
progress-focus. Call it between the long stages of
`build_surrounds`, and inside a loop over clusters or
edges that can run long. A check only at the return is
not enough.

When the build is working on one cluster or one trial
line, the check may name that outline or that line. Do
not name more than one of each. Do not change the
outline the function returns. Do not add conquer.

A host with no hooks still gets the same outlines.

## Checks

`pytest tests/test_surround.py tests/test_progress.py`
with no Inkscape. Skip the window if Qt cannot load.

- The existing surround outlines stay the same.
- A cancel hook set before a long stage raises
  `WeedCancelled` and returns no partial outline to the
  caller.
- A host records at least one check before the function
  returns on a subject with more than one cluster.

## Note

`build_surrounds` still calls `progress.check` before the offset,
again before joins, and on each cluster. Pair, bridge-edge, and
corner loops that can run long still check too. One ring is named
while that cluster is the work. One new bridge edge is named as
the trial line, and that same line stays named while the edge is
tested against the subject. A group that is not one ring is not
named.

`_straighten_colinear` still calls `progress.check(outline=points)`
on each straight side, before the nested walk. `_chain_gap` still
calls `progress.check()` with no name on each sample. `_gap_overlap`
still calls `progress.check()` with no name on each edge of
`ring_a`. The straight-run pair loop there now calls
`progress.check()` with no name once per run of the first ring,
before that run is compared. It does not check every pair. Those
checks name neither ring and no line. `WeedCancelled` is not
caught. The points those functions return are unchanged.
`progress.py` was not extended. Conquer was not added. Solvers,
figures, and the window were not edited.

Why: a check only after that pair loop leaves pause and clear
waiting for it to finish. On a joined 400 by 220 pair,
`_parallel_overlap` there is 2016 by 2016 calls, about a second,
before the per-edge checks. One check per straight run lands
inside that sweep. A check on every pair would be millions of
checks, which is the long work.

Checked with `pytest tests/test_surround.py tests/test_progress.py`:
39 passed, 25.37s. No Inkscape. These tests do not open the
window. With the pair check removed, the three pair assertions
failed: the gap count was 2016 against 4032, the walk recorded
no check while comparisons were still left, and a cancel that
turns true only inside that walk did not raise. After the change
they pass. That cancel raises `WeedCancelled` and the caller gets
no outline. The checks during the walk name nothing. The
straighten and chain tests still pass. With no hooks, the
existing surround tests still match. Status left `in-progress`.

## Summary

No defects remain. The offset, the joins, each cluster, and the
pair, bridge-edge, and corner loops call `progress.check`. The
straighten walk checks once per straight side and names that
ring. The overlap walk checks once per straight run in the pair
sweep, then once per edge of the first ring. The chain walk
checks once per sample. The pair, edge, and chain checks name
nothing. The returned outlines do not change. On the joined fine
pair, the longest gap between checks is about 15ms.

## Context worth keeping

`progress.check` is the hook. It was not extended. A missing name
clears that mark. The host gets a copy. The geometry hook is not
called.

Name a ring only while that one ring is the work. A group of more
than one path is not named. Name one new bridge edge as the trial
line, and pass that same line again while the edge is tested
against the subject. Do not name an edge that already lies on a
ring.

The side-finding scan before the nested straighten walk is short.
`_min_ring_distance` and `_closest_vertices` already check per
point. The straight-run pair loop checks once per run of the
first ring, before the run is compared. It does not check every
pair. On the 400 by 220 pair that sweep is 2016 by 2016
`_parallel_overlap` calls, about 0.9s, and each run is a few
milliseconds. A check on every pair would be millions of checks.

`src/weedlib/solvers.py` is outside this change. Progress runs
there only from `_add_seg`, and only when a segment is accepted.
`debug.phase` checks on enter and exit. That stretch is already
the solver-checks task. The pass is `cr-02.md`.

## Result

No defects remain. The pair walk checks while comparisons are
still left, and a cancel from that check raises `WeedCancelled`
with no outline returned.
`pytest tests/test_surround.py tests/test_progress.py` passed
(39 passed, 25.46s, no Inkscape).
