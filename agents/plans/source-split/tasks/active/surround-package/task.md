# Surround package

**Status:** ready

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

The developer writes what changed, why, and how it was checked.
The reviewer then writes the summary, the context worth keeping,
and the result.
