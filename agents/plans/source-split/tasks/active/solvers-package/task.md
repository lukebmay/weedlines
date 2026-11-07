# Solvers package

**Status:** ready

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

The developer writes what changed, why, and how it was checked.
The reviewer then writes the summary, the context worth keeping,
and the result.
