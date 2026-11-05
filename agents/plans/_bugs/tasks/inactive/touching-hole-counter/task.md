# Touching hole counter

**Status:** done

## Goal

Confirm the report. If it holds, a closed hole that only
touches the outer outline stays the counter.

## Do

- First confirm the report. The review note is not proof.
  Do not verify by reading that note alone.
- The report: a radius-10 circle and a radius-3 circle that
  meet (inner center 7 units out along y=x, within 1e-10)
  do not keep that hole as the counter.
  `inner.subtracted(outer).simplified()` in `_painted_parts`
  in `src/weedlib/figures.py` leaves a triangle of area about
  0.003 in the outer fill, so the inner center stays subject
  and is not weed area. A radius-3 circle centered 6 units
  out, with a gap, stays the counter.
- If it cannot be confirmed, stop. Do not change production
  code. Say that it is not confirmed.
- If it is confirmed, fix it in this task. Follow the counter
  rule in `agents/architecture/preflight.md`. Do not edit
  that file. The hole stays the counter. It is not a
  self-overlap.
- Add the regression in `tests/test_figures.py` only when
  the report is confirmed. No Inkscape. Skip when Qt cannot
  load.
- Do not edit the surround module, the window, or the host.
- `curved-hole-counter` owns the border-crossing change in
  the same file. Do not start this task while that one is
  in progress.

## Checks

- The report is confirmed, or it is not confirmed.
- When it is confirmed: those touching circles keep the hole
  as the counter. The inner center is weed area. The subject
  keeps both rings. The figure check reports no self-overlap.
  The gapped circle centered 6 units out still stays the
  counter.
- `pytest tests/test_figures.py` passes without Inkscape.

## Note

Confirmed. A radius-10 circle and a radius-3 circle that meet
(inner center 7 along y=x) do not keep the hole. The outlines
meet within 2e-10. `inner.subtracted(outer).simplified()` is a
triangle of area about 0.003, so the inner circle was not a
child of the outer. The inner center stayed subject. No
self-overlap was reported. The same circle centered 6 units out
already stayed the counter.

`_outside_fill` still subtracts, then ignores a sliver the outer
fill contains. That sliver is the chord gap of the curve, not
area outside. A point the outer fill does not contain still
blocks the counter. A real crossing is still not a counter,
because the border test is unchanged. The hole is then
subtracted as before.

The touching subject is one contour: the outlines meet, so the
boolean join follows both circles. The figure path still has
both subpaths. The inner center is weed, and the ellipse center
is subject. The gapped circle still has two subject subpaths.

Checked with `pytest tests/test_figures.py`: 24 passed. Qt
loaded. Nothing was skipped. No Inkscape. Status left
in-progress.

Review summary: no defect remains in the change. The named
checks passed. The report is confirmed from the paths. The
touching circles meet within 2e-10, the outlines do not
cross, and the hole stays the counter. The inner center is
weed area. The subject keeps both rings. The figure check
reports no self-overlap. The gapped circle centered 6 units
out stays the counter. A real crossing is not a counter.
The pass is `cr-01.md`.

Context worth keeping: `inner.subtracted(outer).simplified()`
is a triangle of area 0.003157. Its interior point, about
(7.054, 7.054), lies in the outer fill and in the inner
fill. The shared midpoint (7.071, 7.071) is not an interior
point, and `contains` is false there. `_outside_fill`
ignores a leftover whose filled point the outer fill
contains. A point the outer fill does not contain still
blocks the counter. The weed area covers the inner fill:
the areas match, about 25.46, and the subject does not meet
that fill. The figure path has both subpaths. The subject
is one contour because the outlines meet, and that contour
has an element at (-10, 0) and one at the inner circle's
left point. At distance 7.001 the outlines cross and
`_outside_fill` is still false. The border test reports
two self-overlaps, and the inner center stays subject. By
distance 7.08 the leftover sample is outside the outer
fill. At distance 8 the outside cap is subject. Centers
13 apart are not a counter and not a self-overlap. A touch
on the x-axis, at a knot, leaves no leftover and was
already the counter. The surround module, the window, the
host, and the guide were not edited.

One bug is outside this change. Two figures, the same
radius-10 circle and radius-3 circle, centers 7 apart
along y=x. Every sampled point of the inner fill is inside
the outer fill (31397 points, none outside). The outlines
do not cross. Nesting is not a separate-figure overlap,
and a point touch is not an overlap. `_overlap_defects`
in `src/weedlib/figures.py` still uses the area of
`subtracted().simplified()`, which is that same triangle.
The figure check reports one overlap at the inner center,
about (4.950, 4.950). Distance 6 reports none. Distance 8
crosses and the overlap stays. An external touch at 13
reports none. The straight-outline nesting test does not
catch this. Remedy: do not count a leftover the other fill
contains as exclusive area. Do not stop at `_outside_fill`.
From about 7.001 through 7.07 the outlines cross while
that helper is still false. Those pairs must stay
separate-figure overlaps, so a border cross has to keep
the overlap. Not fixed in this pass.

Result: no defect remains in the change. The named checks
passed. One bug is outside the change, in `_overlap_defects`.
`pytest tests/test_figures.py` passed (24 passed, not
skipped). Qt loaded. No Inkscape.
