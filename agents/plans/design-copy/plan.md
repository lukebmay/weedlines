# Design copy

**Rank:** 3

**Stage:** copy

## Goal

The weed-line result's design copy is the same path
records the figure check sees. Correction groups are
omitted. No closepath is added.

## Guide

- [`../../architecture/host.md`](../../architecture/host.md)

## Checks

- The design copy does not include a Weedlines
  corrections group or an id that starts with
  `weedlines-correction`.
- The design copy does not add a closepath that the
  source path did not have.
- The figure check still reads the path records, not
  this design copy.
- Cut geometry is unchanged.
