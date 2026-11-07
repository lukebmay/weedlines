# Source split

**Rank:** 4

**Stage:** split

## Goal

Every product source file and test that is past 1000
lines lives in a directory of smaller files. Each file
owns one responsibility that already has a name. The
public import paths keep working. Frame, grid,
island-hop, and the surround keep today's geometry.
Conquer is not added.

## Guide

- [`../../handbook.md`](../../handbook.md) (Source files)
- [`../../architecture.md`](../../architecture.md)
- [`../../architecture/algorithms.md`](../../architecture/algorithms.md)
- [`../../architecture/preflight.md`](../../architecture/preflight.md)
- [`../../architecture/runtime.md`](../../architecture/runtime.md)

## Checks

- No product source file and no test that this plan
  edits is over 1000 lines, except a generated file or
  one table named in that directory's index.
- `import weedlib` still exposes the names in
  `src/weedlib/__init__.py` `__all__`.
- The figure check does not import the cutter package.
- Progress checks still run inside the figure check,
  the surround, and the solvers, in the child process.
- The geometry tests that moved still pass. A failure
  that is a different cut is a defect.
