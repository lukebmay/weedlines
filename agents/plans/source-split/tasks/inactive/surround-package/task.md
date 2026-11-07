# Surround package

**Status:** done

## Goal

The surround lives in `src/weedlib/surround/`. Geometry
stays as it is. No file this task edits is over 1000
lines.

## Do

The file list is the Surround section of
[`../../../stages/split.md`](../../../stages/split.md),
and the surround-test split in that stage. These are
different files from keep-figures. This task may run
beside it.

Create the package and its README index. Delete
`src/weedlib/surround.py` when the package replaces it.
`surround/__init__.py` re-exports `build_surrounds` and
`_bridge_clears`. Retarget imports.

Every progress check stays on the function that has it
today. Do not change geometry. Do not add the
piece-border clip or conquer. Do not edit
`weedlines.py`.

## Checks

- `tests/test_surround.py`, `tests/test_surround_smooth.py`,
  and `tests/test_surround_bridge.py` pass.
- No file this task edits is over 1000 lines.
- `import weedlib` still exposes `__all__`.
- A different surround is a defect.

## Note

`src/weedlib/surround/` replaces `surround.py`. `build.py` still
dilates, clusters, bridges, and smooths, in today's order.
`offset.py` dilates and takes the outer loops. The ring and
segment primitives the other files share live there, so the
imports do not cycle. `union.py` unions surrounds that meet,
including the gap bridges between outlines. Clearance and that
outline union together are over 1000 lines, so the outline union
stays with the union instead of in `bridge.py`. `bridge.py` is
one inner bridge and its clearance test. `smooth.py` fillets out
to the surround distance. `__init__.py` re-exports
`build_surrounds` and `_bridge_clears`. It also re-exports the
private names the surround tests replace or call on the package:
`_straighten_colinear`, `_gap_overlap`, `_chain_gap`,
`_parallel_overlap`, `_ring_sits_inside`, `_straight_runs`, and
`_straight_side`. The four replacements are looked up on the
package at the call. Progress checks stay on the functions that
had them. Geometry is unchanged. Conquer and the piece-border
clip were not added. `weedlib/__init__.py` and its `__all__`
were not edited.

Tests moved, assertions unchanged, into `tests/test_surround.py`
(offset, join gap, preamble), `tests/test_surround_smooth.py`
(fillets), and `tests/test_surround_bridge.py` (inner bridges
and clearance).

Checked with `pytest tests/test_surround.py tests/test_surround_smooth.py tests/test_surround_bridge.py`:
31 passed in 24.35s. No file this task created is over 1000
lines. `import weedlib` still exposes `build_surrounds`.

Summary: No defects. The surround package keeps the old
geometry. The named tests passed.

Context worth keeping: `build.py` dilates, clusters, bridges,
and smooths, in that order. Gap outlines live in `union.py`
so clearance can stay in `bridge.py` under 1000 lines.
`__init__.py` re-exports `build_surrounds` and `_bridge_clears`,
plus the private names the old tests already used on
`weedlib.surround`: `_straighten_colinear`, `_gap_overlap`,
`_chain_gap`, `_parallel_overlap`, `_ring_sits_inside`,
`_straight_runs`, and `_straight_side`. The four replacements
are looked up on the package at the call. The README does not
list those extras as an API. `weedlib/__init__.py` was not
edited. `figures/`, `keep.py`, `solvers.py`, and `weedlines.py`
were not edited. The surround clip is still absent and stays
with the piece-border plan. The pass is `cr-01.md`.

Result: No defects remain. The named checks passed.
`QT_QPA_PLATFORM=offscreen pytest tests/test_surround.py
tests/test_surround_smooth.py tests/test_surround_bridge.py`:
31 passed in 24.32s. No new bug outside this change.
