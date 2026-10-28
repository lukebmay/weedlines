# Figure overlap

**Status:** ready

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

The developer writes what changed, why, and how it was checked.
The reviewer then writes the summary, the context worth keeping,
and the result.
