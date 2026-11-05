# Touching figures overlap

**Status:** ready

## Goal

Confirm the report. If it holds, two figures that only
touch, with one interior inside the other, are nesting.
They are not a separate-figure overlap.

## Do

- First confirm the report. The review note is not proof.
- The report: a radius-10 circle and a radius-3 circle, as
  two figures, with centers 7 apart along y=x. They meet
  and do not cross. The inner fill lies inside the outer
  fill. `_overlap_defects` in `src/weedlib/figures.py`
  reports one separate-figure overlap at the inner center.
  Distance 6 reports none. Distance 8 crosses and stays an
  overlap.
- If it cannot be confirmed, stop. Do not change production
  code. Say that it is not confirmed.
- If it is confirmed, fix it in this task. A leftover the
  other fill contains is not exclusive area. Do not stop at
  `_outside_fill`. From about 7.001 through 7.07 the
  outlines cross while that helper is still false, and a
  border cross stays a separate-figure overlap. Follow
  `agents/architecture/preflight.md`. Do not edit that file.
- Add the regression in `tests/test_figures.py` only when
  the report is confirmed. No Inkscape. Skip when Qt cannot
  load.
- Do not edit the surround module, the window, or the host.

## Checks

- The report is confirmed, or it is not confirmed.
- When it is confirmed: those two circles at distance 7 are
  not a separate-figure overlap. Distance 6 stays none.
  Distance 8 stays a separate-figure overlap. A pair whose
  outlines cross between about 7.001 and 7.07 stays a
  separate-figure overlap.
- `pytest tests/test_figures.py` passes without Inkscape.

## Note

The developer writes what changed, why, and how it was checked.
The reviewer then writes the summary, the context worth keeping,
and the result.
