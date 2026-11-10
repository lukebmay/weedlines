# Border corners

**Status:** ready

## Goal

Both piece-border rectangles can have rounded corners,
and the surround clip follows the rounded inner border.

## Do

`src/weedlib/piece_border.py` builds the two rectangles.
Round every corner of both when the caller asks, by the
border corner radius. Square corners stay the default
when the caller does not ask. The radius is user units
the caller already converted. Zero is a square corner.
Do not use a radius larger than half the shorter side
of the inner rectangle.

The surround clip and the solver clip follow that inner
path, including the rounded corners. They do not clip
to the axis-aligned bounds of a rounded border. The
border width is still not the clip.

Do not edit the form. Do not edit the guide.

## Checks

- Geometry tests do not need Inkscape.
- With rounding off, both paths are the rectangles the
  library already emits.
- With rounding on, both paths have a corner arc of the
  given radius, and a radius of zero is square.
- A radius above half the inner rectangle's shorter
  side is not used.
- A surround that meets a rounded inner border is
  clipped to that border, not to its bounding box.
- No weed line passes outside the inner border except
  the outer border. Island-hop stays.

## Note

The developer writes what changed, why, and how it was checked.
The reviewer then writes the summary, the context worth keeping,
and the result.
