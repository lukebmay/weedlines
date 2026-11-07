# Solvers package

**Status:** done

## Goal

Frame, grid, and island-hop live in `src/weedlib/solvers/`.
Hosts still call `generate_weeds`. No file this task
edits is over 1000 lines.

## Do

Start after keep-figures. `solvers/__init__.py`
re-exports the public keep names from `weedlib.keep`.

The file list is the Solvers section of
[`../../../stages/split.md`](../../../stages/split.md),
and the `tests/test_weeds.py` split in that stage.
Retarget patches in `tests/test_progress.py` to the
defining module. That file stays one file.

Create the package and its README index. Delete
`src/weedlib/solvers.py` when the package replaces it.
The package re-exports the names `weedlib` already
exports from solvers, plus `frame_weeds`, `grid_weeds`,
and `island_hop_weeds`. It does not re-export private
helpers.

`auto` stays island-hop. `region` stays grid. An unknown
mode stays frame. `_add_seg` and `_publish_path_segments`
stay the only segment reports. A stage does not grow its
own pause flag. Do not edit `weedlines.py`.

## Checks

- The weeds tests named in the stage pass:
  `tests/test_frame.py`, `tests/test_grid.py`,
  `tests/test_keep.py`, `tests/test_island.py`,
  `tests/test_peel.py`, `tests/test_bays.py`,
  `tests/test_corridors.py`, `tests/test_ties.py`,
  `tests/test_emit.py`, and `tests/test_traps.py`.
  Shared shapes live in `tests/weed_shapes.py`.
- `tests/test_progress.py` passes, with private-helper
  patches aimed at the defining module.
- No file this task edits is over 1000 lines.
- `import weedlib` still exposes `__all__`.
- A different cut is a defect.

## Note

`src/weedlib/solvers.py` is now the package `src/weedlib/solvers/`.
Each stage file is one responsibility. `rules.py` holds the mode
list and the numeric floors. `dispatch.py` holds `generate_weeds`,
the mode switch, and frame. `auto` still runs island-hop, `region`
still runs grid, and an unknown mode still runs frame.
`__init__.py` re-exports the names `weedlib` already imports from
solvers, plus the public keep names `even_odd_keep_fill`,
`design_keep_fill`, `list_closed_subpaths`, `padded_work_rect`,
and `closed_fill_union`. It does not re-export private helpers.

A call that leaves its module uses the defining module's attribute
(`_sol_emit._add_seg`, and the same for the other modules). A call
that stays in the module uses the bare name, so a patch of that
module is the patch the run sees. `_add_seg` still takes
`report=False` for the seen-path copy. `_publish_path_segments`
is the other report. Both live in `emit.py`. No stage grew a pause
flag; the others call `emit._progress_check`. Island-hop's
`phase()` blocks and `_hole_internal_splits` stay in `island.py`.
Frame and grid do not import clipper. Ring conversion
(`_path_to_rings`, `_rings_to_path`, `_ensure_ccw`, `_rect_as_ring`)
and `_add_line_segs` live in `geom.py`, which does not import a
sibling. `emit.py` is 721 lines, so `cleanup.py` was not added.
`rank.py` and `bay.py` stay one file each.

`tests/test_weeds.py` moved into the stage's test files.
`tests/weed_shapes.py` holds the shared shapes. Assertions were
not rewritten. A private name is imported from the module that
defines it, and `weeds_mod._private` now names that module.
`tests/test_progress.py` stays one file. Its patches aim at
`gaps._mouth_seal`, `emit._seg_emit_ok`, `pockets._body_pocket_seals`,
and `emit._drop_parallel_hugs`. `keep.py`, `figures/`, `surround/`,
the dialog package, and `weedlines.py` were not edited.

Why: one solvers module was past 1000 lines. The split follows the
named responsibilities and leaves the cuts where they were.

Checked with `QT_QPA_PLATFORM=offscreen pytest tests/test_frame.py
tests/test_grid.py tests/test_keep.py tests/test_island.py
tests/test_peel.py tests/test_bays.py tests/test_corridors.py
tests/test_ties.py tests/test_emit.py tests/test_traps.py
tests/test_progress.py`: 153 passed, 4 skipped. The skips are the
existing Inkcut job-pipeline marks. `wc -l` on the new modules:
largest is `tests/test_bays.py` at 876 and `emit.py` at 721. None
over 1000. `import weedlib` still exposes the same `__all__`.
Status left `in-progress`.

Summary: No defects. The solvers package keeps the old cuts.
The named tests passed.

Context worth keeping: `dispatch.py` maps `auto` to island-hop,
`region` to grid, and an unknown mode to frame. Frame stays
there. `grid.py` does not import clipper. `_add_seg` and
`_publish_path_segments` are the only segment reports, both in
`emit.py`, and `report=False` still marks the seen-path copy.
Stages call `emit._progress_check` and did not grow a pause
flag. `phase()` blocks and hole splits stay in `island.py`.
`emit.py` is 721 lines, so `cleanup.py` was not added.
`solvers/__init__.py` re-exports the public solver names and
the public keep names, not private helpers. A cross-module
call uses the defining module's attribute, so a patch of that
module is the patch the run sees. `tests/test_weeds.py` is
gone. Assertions were moved. Progress patches name `gaps`,
`emit`, and `pockets`. `keep.py`, `figures/`, `surround/`,
the dialog, and `weedlines.py` were not edited. The pass is
`cr-01.md`.

Result: No defects remain. The named checks passed.
`QT_QPA_PLATFORM=offscreen pytest` on the eleven named files:
153 passed, 4 skipped, in 122.88s. The skips are the old
Inkcut job-pipeline marks.

Outside this change: `agents/architecture/algorithms.md`
still says private helpers live in `solvers.py`. That file
is gone. The package is `src/weedlib/solvers/`. Not edited
here.
