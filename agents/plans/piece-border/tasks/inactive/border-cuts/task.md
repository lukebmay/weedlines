# Border cuts

**Status:** done

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

`generate_weeds` takes `inner_distance` and `border_width`.
Both default to omitted. Omitting either one leaves the mode
path and its published segments unchanged. When both are set,
it calls `piece_border` and clips the mode lines to that
inner rectangle. A published segment in `emit.py` uses the
same rectangle clip, and that clip is off when the lengths
are omitted. The two rectangles are appended after the
clipped lines, inner then outer, and they are not clipped.
An empty keep still returns an empty path.

Why: the outer rectangle is the only geometry outside the
inner one, and the pair stays together. The stored island-hop
seal is an internal value. `_add_seg` still writes the whole
segment into the working path, so ranking and clearance stay
as they were. The clip is the published copy and the path
`generate_weeds` returns. A crossing seal from `(20, 0)` to
`(20, -12)` stays that length in the solver. The returned
line and the published line end at `(20, -6)`, on the inner
edge.

Checked again with `QT_QPA_PLATFORM=offscreen python3 -m pytest
tests/test_border_cuts.py tests/test_frame.py`: 11 passed,
2 skipped, in 0.22s. The skips are the two Inkscape job
tests already skipped in `test_frame.py`. No Inkscape.
`src/weedlib/piece_border.py` is unchanged. The solver diff
is `dispatch.py` and `emit.py`.

Summary: No defects. The stored seal is not what the host
sees. Returned and published lines stay inside the inner
rectangle except the outer border. The named tests passed
again.
