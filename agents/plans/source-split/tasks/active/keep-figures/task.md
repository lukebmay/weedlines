# Keep and figures

**Status:** in-progress

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

The developer writes what changed, why, and how it was checked.
The reviewer then writes the summary, the context worth keeping,
and the result.
