# Subject and weed

**Status:** done

## Goal

The library names the subject, the weed area, and the design
bounds from the figures. Swap exchanges the two regions inside
those bounds.

## Do

- Add the region call on `src/weedlib/figures.py` that the window
  will use. It takes the classified figures and a swap flag.
- Do not reimplement figure classification. Do not edit
  `src/weedlib/solvers.py`.
- The rules are Subject and weed area in
  `agents/architecture/preview.md`. Swap does not change defects
  (`agents/architecture/preflight.md`).
- Add the cases to `tests/test_figures.py`.

## Checks

- Painted interiors start as subject. An interior with no paint
  starts as weed area. When no figure has paint, every interior
  starts as subject.
- Weed area is the design bounds minus the subject, including gaps
  and holes, and not the sheet outside the bounds.
- The two cases in that preview section hold. A second swap
  restores the first assignment. The bounds do not move.
- Swap does not add or remove defects from `classify_figures`.
- `pytest tests/test_figures.py` passes without Inkscape. Skip
  only when Qt cannot load.

## Note

`subject_weed_regions(figures, swap)` is the region call. `figures`
is the list from `classify_figures`. `swap` false is the starting
assignment; true exchanges subject and weed area. The same figures
with false again restore that assignment. Do not pass the returned
paths back in.

It returns `SubjectWeed`: `subject` and `weed_area` are
`QPainterPath`s, and `bounds` is the `QRectF` of every figure.
Painted interiors, from the same `_painted_parts` the figure check
uses, start as subject. `none` is not paint; a color or `other` is.
When no figure has paint, every interior is subject. Weed area is
that box minus the subject, so gaps and holes are included and the
sheet outside the box is not. Swap only exchanges those two paths.
It does not move `bounds` and it does not reclassify defects.
`src/weedlib/solvers.py` is unchanged.

Checked with `pytest tests/test_figures.py` (14 passed). Qt loaded;
nothing was skipped.

Review summary: no defects remain. The change matches the task.
`subject_weed_regions(figures, swap)` names the subject, the weed
area, and the design bounds. Painted interiors start as subject.
An interior with no paint starts as weed area unless a painted
interior already covers it. With no paint, every interior is
subject. Weed area is the box minus the subject. Swap exchanges
those two paths, and the flag false restores them. Bounds and
defects stay put. The two preview cases hold.

Context worth keeping: `SubjectWeed` is `subject`, `weed_area`,
and `bounds`. `figures` is the list from `classify_figures`. Do
not pass the returned paths back in. `none` is not paint; a color
or `other` is. Interiors come from `_painted_parts`, including
the painted close of an open subpath. Both paths use odd-even
fill, so a hole stays a hole. The letter case is a stroke-only
frame plus painted letters. The band case is one filled path
whose counters are the letters. Swap true twice stays exchanged.
A null bounding rect, such as a lone moveto, does not grow the
box. `src/weedlib/solvers.py` is unchanged.

Result: no defects remain. The named checks passed.
`pytest tests/test_figures.py` passed (14 passed, not skipped).
Qt loaded. The tests do not load Inkscape. `src/weedlib/solvers.py`
has no test; its diff is empty.
