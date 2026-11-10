# Concavity

**Rank:** 4

**Stage:** explore

## Goal

The library can compute candidate numbers for a cavern
fast enough to run while the person is looking. A
candidate is not a measure the algorithms part has
named, and it does not seal a cavern. This plan does
not emit a weed line and does not change the surround
outline. Concrete measures and thresholds, once they
exist, are written into the algorithms part before any
cut uses them.

## Guide

- [`../../architecture/algorithms.md`](../../architecture/algorithms.md)
- [`../../architecture/glossary.md`](../../architecture/glossary.md)
- [`../../architecture/boundary.md`](../../architecture/boundary.md)

## Checks

- A candidate is local to the outline. It does not
  search over sets of caverns.
- One cavern may produce more than one number.
- A rectangle has no cavern to score. A hole loop is
  not a cavern. The open piece-border clip is not a
  cavern.
- No candidate is written into the guide from this
  plan. [`notes.md`](notes.md) holds probes. Open it
  when the task says the attempt matters.
- This plan does not bridge a mouth, does not cut a
  cavern up, and does not start conquer or the
  surround coastline.
