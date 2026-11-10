# Piece border

**Rank:** 4

**Stage:** border

## Goal

Every algorithm can cut the piece border around the
piece, and the window paints that border when the figure
check is clear. The form shows Border Padding, Border
Width, and Border Rounded Corners. The radius shows
while that box is on. The surround clip follows the
inner border. The surround does not cut the subject.
Island-hop stays.

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
- A change to border padding, the checkbox, or the radius
  repaints the border and, when a surround is showing,
  asks for that surround. The border width asks for the
  border only. Swap asks for the border again.
- The labels are Border Padding, Border Width, Border
  Rounded Corners, and Border Corner Radius. The radius
  starts at one quarter of an inch and shows only while
  the box is on.
- Each border length is the real length in the boundary
  part. The radius is at most half the shorter side of
  the inner rectangle.
- Do not remove island-hop. No weed line passes outside
  the inner border except the outer border.
- The border is not a surround, not the surround distance,
  and not the padding of frame, grid, or island-hop.
- Geometry tests do not need Inkscape. Window tests run
  offscreen when Qt is available.
- The user page that shows the border matches the preview
  part, including the four control names.
