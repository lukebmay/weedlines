# Figure overlap

**Status:** done

## Goal

The same figure check also reports separate-figure overlap and
self-overlap, and it does not stop at the first defect.

## Do

- Extend `classify_figures` in `src/weedlib/figures.py`. Add cases
  to `tests/test_figures.py`.
- Each separate-figure overlap target is a point inside that shared
  region. Each self-overlap target is the crossing point. Keep the
  dangling-end targets from the figure-check task.
- Do not take a subject or swap argument. Do not edit
  `src/weedlib/solvers.py`. Do not build arrow paths.
- The rules are the three defects in
  `agents/architecture/preflight.md`.

## Checks

- One result can hold a dangling end, a separate-figure overlap,
  and a self-overlap together.
- Nesting is not an overlap. A point touch is not. A shared
  boundary with no shared area is not.
- Each connected shared area is one overlap. Two subpaths of one
  element that cross are a self-overlap of that figure. A hole
  whose outline does not cross the outer outline is not.
- The same records always produce the same defects.
- `pytest tests/test_figures.py` passes without Inkscape. Skip
  only when Qt cannot load.

## Note

`classify_figures` still takes only the path records. It now reports
separate-figure overlaps and self-overlaps along with dangling ends,
and it does not stop at the first. An overlap target is a point inside
one connected shared area. Nesting, a point touch, and a shared boundary
with no area are not overlaps. A counter whose border does not cross
stays out of the interior; the lens where two subpaths cross stays in,
so that lens does not split one shared area. A self-overlap target is a
proper crossing of the real border, including two subpaths of one
element. The segment an open subpath is painted as if closed by is not
a border. Kinds are `dangling`, `overlap`, and `self-overlap`.
`src/weedlib/solvers.py` is unchanged.

Checked with `pytest tests/test_figures.py` (8 passed). Qt loaded;
nothing was skipped.

Review summary: two defects. The change matches the task, and
today's code matches the change, but two preflight rules have no
test. A one-subpath bowtie is a self-overlap. The painted closing
chord is not a border when it is the only crossing. Each rule can
fail while `tests/test_figures.py` stays green. Remedy for each:
add the test, and fix the code if the test fails.

Context worth keeping: `classify_figures(records)` returns
`FigureCheck`. Kinds are `dangling`, `overlap`, and
`self-overlap`. An overlap target is one point in one connected
shared area. Nesting, a point touch, and a shared boundary are
not overlaps. A contained subpath whose real border does not
cross is a counter and stays out of the interior. The lens of two
crossing subpaths stays in the interior. A self-overlap is a
proper crossing of real border segments, including two segments
of one subpath. The painted close is not a segment. A closed
bowtie `M 0,0 L 10,10 L 0,10 L 10,0 Z` crosses at (5, 5); today's
code reports that point. Square `M 0,0 L 4,0 L 4,4 L 0,4 Z` plus
`M -1,2 L -1,5 L 5,5 L 5,2` has painted crossings at (0, 2) and
(4, 2); today's code reports only dangling ends at (-1, 2) and
(5, 2). Skipping same-subpath pairs, or appending that chord,
does not change the current fixtures. No subject or swap
argument. `src/weedlib/solvers.py` is unchanged.

Result: two defects remain. The named checks passed.
`pytest tests/test_figures.py` passed (8 passed, not skipped).
The one-subpath crossing and the painted closing chord are the
checks with no test. `src/weedlib/solvers.py` has no test; its
diff is empty.

Added the two missing cases in `tests/test_figures.py`. A closed
bowtie `M 0,0 L 10,10 L 0,10 L 10,0 Z` is one self-overlap at
(5, 5). Square `M 0,0 L 4,0 L 4,4 L 0,4 Z` plus open
`M -1,2 L -1,5 L 5,5 L 5,2` is only dangling ends at (-1, 2) and
(5, 2); the painted chord is not a border. Both already matched
`classify_figures`, so `src/weedlib/figures.py` was not changed.
`src/weedlib/solvers.py` was not changed. Checked with
`pytest tests/test_figures.py` (10 passed). Qt loaded; nothing
was skipped.

Review summary: no defects remain. The two missing tests are in
`tests/test_figures.py`, and `src/weedlib/figures.py` was not
changed for them. A closed bowtie `M 0,0 L 10,10 L 0,10 L 10,0 Z`
is one self-overlap at (5, 5). Square `M 0,0 L 4,0 L 4,4 L 0,4 Z`
plus open `M -1,2 L -1,5 L 5,5 L 5,2` is only dangling ends at
(-1, 2) and (5, 2). The painted chord is not a border.

Context worth keeping: `test_one_subpath_bowtie_is_a_self_overlap`
fails if same-subpath pairs are skipped. The bowtie is one ring,
and the crossing is its two non-adjacent diagonals.
`test_painted_closing_chord_is_not_a_border` fails if the chord
from (5, 2) to (-1, 2) is a border; that also reports
self-overlaps at (0, 2) and (4, 2). The open polygon is
`(-1, 2), (-1, 5), (5, 5), (5, 2)` and does not include that
chord. `src/weedlib/solvers.py` is unchanged.

Result: no defects remain. The named checks passed.
`pytest tests/test_figures.py` passed (10 passed, not skipped).
Qt loaded. The tests do not load Inkscape.
