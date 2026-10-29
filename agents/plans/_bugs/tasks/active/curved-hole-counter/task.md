# Curved hole counter

**Status:** ready

## Goal

A closed hole whose outline does not cross the outer outline
stays the counter. It is not a self-overlap.

## Do

- The miss is in `src/weedlib/figures.py`. The border test uses
  chord vertices from `toSubpathPolygons`. On a radius-10
  ellipse those chords sit inside the curve. A triangular hole
  with a vertex between the curve and a chord is reported as
  two self-overlaps, and the counter is dropped.
- Follow the self-overlap rule in
  `agents/architecture/preflight.md`. Do not edit that file.
- Add the regression in `tests/test_figures.py`. No Inkscape.
  Skip when Qt cannot load.
- Do not edit the surround module, the window, or the host.

## Checks

- That ellipse and triangle return no self-overlap. The hole
  stays the counter: the subject keeps both rings, and the
  triangle's centroid is weed.
- The same triangle moved inward so it clears the chords still
  returns no self-overlap.
- `pytest tests/test_figures.py` passes without Inkscape.

## Note

The developer writes what changed, why, and how it was checked.
The reviewer then writes the summary, the context worth keeping,
and the result.
