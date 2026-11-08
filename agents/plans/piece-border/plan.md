# Piece border

**Rank:** 4

**Stage:** border

## Goal

Every algorithm can cut the piece border around the
piece, and the window paints that border when the figure
check is clear. The two length options update that
preview once their labels are named. The surround clip
uses the inner rectangle. The surround does not cut the
subject. Island-hop stays.

## Guide

- [`../../architecture/algorithms.md`](../../architecture/algorithms.md)
- [`../../architecture/preview.md`](../../architecture/preview.md)
- [`../../architecture/boundary.md`](../../architecture/boundary.md)
- [`../../architecture/glossary.md`](../../architecture/glossary.md)

## Checks

- The piece border and the surround clip match the
  algorithms part.
- The preview paints both rectangles when the figure
  check is clear, without waiting for Start. The window
  does not build them.
- A change to either length repaints the border. Only the
  inner distance asks again for a surround that is
  already showing. The border width does not. Swap asks
  for the border again.
- The two option labels stay unnamed until the human
  names them. Until then the form does not show those
  options, and the library still emits the defaults.
- Each border length is the real length in the boundary
  part.
- Do not remove island-hop. No weed line passes outside
  the inner rectangle except the outer border rectangle.
- The border is not a surround, not the surround distance,
  and not padding.
- Geometry tests do not need Inkscape. Window tests run
  offscreen when Qt is available.
- The user page that shows the border matches the preview
  part. Do not invent the two labels there.
