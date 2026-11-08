# Concavity

**Rank:** 4

**Stage:** measure

## Goal

The algorithms part names how a cavern is measured. The
person sets that measure as one length, the cavern
allowance. Every algorithm can read it. This plan does
not emit a weed line and does not change the surround
outline.

## Guide

- [`../../architecture/algorithms.md`](../../architecture/algorithms.md)
- [`../../architecture/glossary.md`](../../architecture/glossary.md)
- [`../../architecture/boundary.md`](../../architecture/boundary.md)

## Checks

- The measure is one length per cavern, in document user
  units, and it scales when the outline scales.
- The outline fails on its worst cavern. A mild cavern
  can stay. A hole loop is not a cavern. The open
  piece-border clip is not a cavern.
- The allowance is not the surround distance, the join
  gap, or either piece-border length.
- Mouth and reach are constructions two implementers
  would share before they are written into the guide.
  Until then the guide does not name the formula.
- The candidate in [`notes.md`](notes.md) is not the
  guide. Open it when the task says the attempt matters.
- This plan does not bridge a mouth and does not cut a
  cavern up. Conquer stays unspecified.
