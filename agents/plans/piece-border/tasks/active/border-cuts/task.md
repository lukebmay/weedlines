# Border cuts

**Status:** ready

## Goal

Every mode's weed lines stay inside the inner rectangle.
The two border rectangles are the exception, and they
are emitted together.

## Do

`generate_weeds` in `src/weedlib/solvers/dispatch.py`
gains `inner_distance` and `border_width`. Both default
so a caller that omits them still gets today's path.
When both are passed, call `piece_border`. Do not
reimplement the rectangles. Do not edit
`src/weedlib/piece_border.py`.

Clip the mode's lines so none pass outside the inner
rectangle. A published segment uses that same clip, in
`src/weedlib/solvers/emit.py`, which already accepts or
drops a segment. Do not split `emit.py`. You may call
the rectangle clip in `src/weedlib/solvers/clip.py`. Do
not change that file. When the lengths are omitted, a
published segment is unchanged.

Emit the two rectangles together, inner then outer,
after the clipped lines. Nothing else sits between
them. Do not run the pair through the clip. The outer
rectangle is the only geometry outside the inner
rectangle.

Island-hop stays a mode. Do not change its pass order,
ranking, or clearance except for this clip. Do not
invent conquer cuts. Do not name a cavern measure. Do
not take a measure from `docs/weed-hard-rules.md`. Do
not edit the window, `src/weedlib/surround/`, or the
solvers README. The border is not padding.

Tests go in `tests/test_border_cuts.py`. No Inkscape.
Skip when Qt cannot load. Do not retarget
`tests/test_frame.py`.

## Checks

- Omitting the two lengths leaves today's path. A
  published segment on that path is unchanged.
- With both lengths, no returned or published line
  passes outside the inner rectangle except the outer
  border rectangle. The pair is inner then outer, with
  nothing between them.
- Frame and grid show the clip. Island-hop still runs
  when pyclipper is present, and may skip when it is
  missing. An empty keep emits nothing.
- `pytest tests/test_border_cuts.py tests/test_frame.py`
  passes without Inkscape. `src/weedlib/piece_border.py`
  is unchanged.

## Note

The developer writes what changed, why, and how it was checked.
The reviewer then writes the summary, the context worth keeping,
and the result.
