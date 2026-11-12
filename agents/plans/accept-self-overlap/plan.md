# Accept self-overlap

**Rank:** 4

**Stage:** gate

## Goal

The window follows the preflight gate. An accepted
self-overlap may start, and a dangling end or a
separate-figure overlap still blocks. Accepting does
not rewrite the path. The fix is the host proposal.
It is not built in this stage. Conquer stays off.

## Guide

- [`../../architecture/preflight.md`](../../architecture/preflight.md)
- [`../../architecture/preview.md`](../../architecture/preview.md)
- [`../../architecture/host.md`](../../architecture/host.md)
- [`../../architecture/algorithms.md`](../../architecture/algorithms.md)

## Checks

- The window follows the preflight gate.
- An accepted self-overlap may start, and a dangling
  end or a separate-figure overlap still blocks.
- Accepting does not rewrite the path. The fix is
  the host proposal. It is not built in this stage.
  Conquer stays off.
- No solver change. The window is not built until
  the human asks.
