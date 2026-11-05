# Touching hole counter

**Status:** ready

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

The developer writes what changed, why, and how it was checked.
The reviewer then writes the summary, the context worth keeping,
and the result.
