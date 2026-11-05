# Shallow overlap

**Status:** ready

## Goal

Confirm the report. If it holds, two figures whose
outlines cross and whose interiors partially intersect
are a separate-figure overlap, even when the intersection
polygon has no area.

## Do

- First confirm the report. The review note is not proof.
- The report: a radius-10 circle and a radius-3 circle, as
  two figures, with centers 12.97 apart along y=x. The
  outlines cross. A point near (7.064, 7.064) lies in both
  fills, and each fill has a point outside the other.
  `intersected().simplified()` in `_overlap_defects` in
  `src/weedlib/figures.py` has no area. The function
  returns before the outline test, so the figure check
  reports no separate-figure overlap. Distance 12.96
  reports one. Distance 13 reports none.
- If it cannot be confirmed, stop. Do not change production
  code. Say that it is not confirmed.
- If it is confirmed, fix it in this task. When the
  outlines cross and each fill contains a point of the
  other, report one separate-figure overlap. The target
  is a point both fills contain. An empty intersection
  polygon does not erase that. Follow
  `agents/architecture/preflight.md`. Do not edit that
  file.
- Add the regression in `tests/test_figures.py` only when
  the report is confirmed. No Inkscape. Skip when Qt cannot
  load.
- Do not edit the surround module, the window, or the host.
- Distance 7 of these circles is nesting. Do not make that
  touch a separate-figure overlap.

## Checks

- The report is confirmed, or it is not confirmed.
- When it is confirmed: distance 12.97 is one
  separate-figure overlap, and the target is a point both
  fills contain. Distance 12.96 stays one. Distance 13
  stays none. Distance 7 stays nesting, not a
  separate-figure overlap.
- `pytest tests/test_figures.py` passes without Inkscape.

## Note

The developer writes what changed, why, and how it was checked.
The reviewer then writes the summary, the context worth keeping,
and the result.
