# Surround cavern

**Rank:** 4

**Stage:** coastline

## Goal

The surround coastline traces a cavern within the
allowance at the surround distance, and crosses the
mouth of a cavern over the allowance without coming
closer than that distance. The piece-border clip still
holds. This step does not cut a bridged cavern up.
Conquer stays unspecified.

## Guide

- [`../../architecture/algorithms.md`](../../architecture/algorithms.md)
- [`../../architecture/preview.md`](../../architecture/preview.md)
- [`../../architecture/boundary.md`](../../architecture/boundary.md)

## Checks

- A cavern within the allowance stays on the offset.
  A cavern over the allowance is crossed at the mouth.
  The bridge is never closer than the surround
  distance, except at an open clip end the algorithms
  part already allows.
- A hole loop is not bridged. The open clip gap is not
  a cavern and is not closed.
- The bridge keeps a smooth corner. The join gap, the
  surround distance, and the border lengths keep their
  own meanings.
- This plan does not start until the algorithms part
  names a cavern measure and its threshold. A probe in
  the concavity plan is not that name. The inner
  border is in place.
- Conquer stays unspecified. Geometry tests do not
  need Inkscape.
