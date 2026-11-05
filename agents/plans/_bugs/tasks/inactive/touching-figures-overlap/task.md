# Touching figures overlap

**Status:** done

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

The report is confirmed. Two figures, a radius-10 circle and a
radius-3 circle with centers 7 apart along y=x, meet within
2e-10. The outlines do not cross. The inner subtraction is a
sliver of area about 0.00316 whose filled point the outer fill
still contains, so `_outside_fill` is false. `_overlap_defects`
treated that sliver as exclusive area and reported one overlap
at the inner center, about (4.950, 4.950). Distance 6 reports
none. Distance 8 crosses and stays an overlap. From 7.001
through 7.07 the outlines cross while `_outside_fill` is still
false.

Exclusive area now uses `_outside_fill`, so a leftover the
other fill contains is not a point outside it. A cross of the
real outlines still counts. That keeps the shallow crossings
as separate-figure overlaps, and a contained touch is nesting.

Checked with `pytest tests/test_figures.py`: 25 passed. Qt
loaded. No Inkscape. The surround module, the window, the
host, and the guide were not edited. The touching-hole
counter test was not changed.

Review summary: no defect remains in the change. The named
checks passed. The contained touch is nesting. Distance 6
reports none. Distance 8 is a separate-figure overlap.
From 7.001 through 7.07 the outlines cross while
`_outside_fill` is false, and that cross keeps one
separate-figure overlap. The pass is `cr-01.md`.

Context worth keeping: Centers 7 apart along y=x meet
within 2e-10. The outlines do not cross. The inner
subtraction is a sliver of area 0.003157 whose filled
point, about (7.054, 7.054), lies in the outer fill.
Exclusive area uses `_outside_fill` both ways, then
`_outlines_cross` on the two figures' borders when the
intersection has area. At 7.0001 the outlines already
cross and `_outside_fill` is still false. By 7.08 the
leftover sample lies outside the outer fill. Centers
6.999 and 6.9999 apart along y=x are nesting. A touch on
the x-axis leaves no sliver. An external touch at
distance 13 is not an overlap. The product diff is
`src/weedlib/figures.py` and `tests/test_figures.py`.

One bug is outside this change. Two figures, the same
radius-10 circle and radius-3 circle, centers 12.97 apart
along y=x. The outlines cross twice. The point about
(7.064, 7.064) lies in both fills. The inner center,
about (9.171, 9.171), lies outside the outer fill, and
the origin lies outside the inner fill. The interiors
partially intersect, so the pair is a separate-figure
overlap. `intersected().simplified()` in
`_overlap_defects` has no area, and the function returns
before the outline test, so the figure check reports no
defect. Distance 12.96 still reports one. Distance 13
does not. That empty-intersection return was already
there. Remedy: when the outlines cross and each fill
contains a point of the other, report one
separate-figure overlap even if the intersection has no
area. The target is a point both fills contain. Not
fixed in this pass.

Result: No defect remains in the change. The named checks
passed. One bug is outside the change, in
`_overlap_defects`. `pytest tests/test_figures.py` passed
(25 passed). Qt loaded. No Inkscape.
