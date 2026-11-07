# Keep and figures

**Status:** done

## Goal

The figure check and the one twin collapse live outside
the cutter. The figure tests still pass, and no file this
task edits is over 1000 lines.

## Do

The file list is the Keep and Figures sections of
[`../../../stages/split.md`](../../../stages/split.md),
plus the figure-test split in that stage.

Create `src/weedlib/keep.py` and `src/weedlib/figures/`
with its README index and an `__init__.py` that
re-exports the names the stage lists. Delete
`src/weedlib/figures.py` when the package replaces it.
Retarget imports.

`keep.py` is the one twin collapse. `figures/check.py`
calls it and does not import solvers. Until `solvers/`
exists, `solvers.py` re-exports the public keep names
from `weedlib.keep`. Do not leave a second collapse.
Do not give the collapse to `paths.py`. Do not edit
`weedlines.py`.

Split `tests/test_figures.py` into `tests/test_figures.py`,
`tests/test_self_overlap.py`, and `tests/test_overlap.py`.

The progress checks the stage names stay on the function
that has them today.

## Checks

- `tests/test_figures.py`, `tests/test_self_overlap.py`,
  and `tests/test_overlap.py` pass.
- No file this task edits is over 1000 lines.
- `import weedlib` still exposes `__all__`.
- The figure check does not import the cutter package.

## Note

`src/weedlib/keep.py` owns closed subpaths, the one twin collapse,
nesting, keep fill, and the padded work rect. The area and sample
helpers those functions call moved with them, so keep does not
import the cutter. `solvers.py` deletes its copies and imports
the names back. Public names re-exported there are
`even_odd_keep_fill`, `design_keep_fill`, `closed_fill_union`,
`list_closed_subpaths`, and `padded_work_rect`. The cutter still
calls the private helpers through that same import, so tests
that import them from `weedlib.solvers` keep working. There is
one collapse.

`src/weedlib/figures/` replaces `figures.py`. `check.py` calls
`keep._dedupe_closed_subpaths` and `keep._subpath_is_closed`.
No file under `figures/` imports solvers. Calls that the figure
tests replace (`_self_overlap_defects`, `_piece_hits`,
`_one_point_per_region`, `_meets_region`, `_sample_sets_meet`,
`_linked_mark_groups`, `_marks_share_region`) are looked up on
the figures package at the call, so those tests did not have to
change. Progress checks stay on `_without_twins`,
`_overlap_defects`, `_one_point_per_region`,
`_linked_mark_groups`, and `_self_overlap_defects`.

`weedlib/__init__.py` still exports the same `__all__`. The four
keep names in that list now come from `keep`.

Figure tests moved, unchanged, into `tests/test_figures.py`,
`tests/test_self_overlap.py`, and `tests/test_overlap.py`.
Shared helpers went with the tests that use them.

`solvers.py` is still 7382 lines. It started over 1000, and this
task does not split it. That is the solvers package.

Checked with `pytest tests/test_figures.py tests/test_self_overlap.py tests/test_overlap.py`:
40 passed. Five keep tests in `tests/test_weeds.py` passed
(`test_even_odd_letter_o_keep_is_ring`,
`test_overlapping_design_stays_keep`,
`test_frame_weeds_padded_rect`,
`test_polyline_samples_curves_not_control_points`,
`test_fill_stroke_twins_deduped_for_framed_keep`).
Collection of `test_weeds.py`, `test_progress.py`, and the
window tests that import figures succeeded. `wc -l`: keep 308,
types 41, check 281, interior 218, borders 894, overlap 903,
test_figures 611, test_self_overlap 353, test_overlap 720.
None of those is over 1000. `import weedlib` exposes the same
`__all__`. The figure package does not import solvers.

Summary: No defects. The figure check and the one twin collapse
live in `figures/` and `keep.py`. The figure tests passed, and
the defect rules did not change.

Context worth keeping: `_dedupe_closed_subpaths` is defined only
in `keep.py`. `solvers.py` imports the public keep names and the
private helpers the cutter still calls. It does not define those
bodies, and it does not re-export the collapse.
`figures/` does not import solvers. Progress checks stay on
`_without_twins`, `_overlap_defects`, `_one_point_per_region`,
`_linked_mark_groups`, and `_self_overlap_defects`. Tests that
replace a figure helper still patch `weedlib.figures`, and the
call looks that name up on the package. `keep._interior_point`
takes a path. `figures` interior `_interior_point` takes a point
and two fills. They are not the same helper. `tests/README.md`
lists the test files that exist and does not name the later
splits. `solvers.py` stays over 1000 lines. That split is the
solvers package. The pass is `cr-01.md`.

Result: No defects remain. The named checks passed.
`QT_QPA_PLATFORM=offscreen pytest tests/test_figures.py
tests/test_self_overlap.py tests/test_overlap.py`: 40 passed
in 11.90s. No bug outside this change.
