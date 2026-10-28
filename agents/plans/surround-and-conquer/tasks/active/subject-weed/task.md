# Subject and weed

**Status:** ready

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

The developer writes what changed, why, and how it was checked.
The reviewer then writes the summary, the context worth keeping,
and the result.
