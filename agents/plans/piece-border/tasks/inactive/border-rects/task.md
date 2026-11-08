# Border rects

**Status:** done

## Goal

The library builds the two piece-border rectangles from
the subject and the two lengths. It does not paint, and
it does not clip.

## Do

Add `piece_border(subject, inner_distance, border_width)`
in `src/weedlib/piece_border.py`. Export it from
`src/weedlib/__init__.py`.

`subject` is the subject path the window already has, in
document user units. The two lengths are user units the
caller supplies. This function does not convert inches
and does not read a scale. Return the inner rectangle,
then the outer one. An empty subject returns nothing.

The geometry is Piece border in
`agents/architecture/algorithms.md`. Units are
`agents/architecture/boundary.md`. The piece is the
subject. The piece size is that subject's axis-aligned
bounds, not the page and not a figure outside the
subject. The inner rectangle is those bounds expanded by
`inner_distance` on every side. The outer rectangle is
the inner one expanded by `border_width` on every side.

Do not clip a surround. Do not call `generate_weeds`.
Do not edit `src/weedlib/figures/`, `src/weedlib/surround/`,
`src/weedlib/solvers/`, the window, or `docs/`. Do not
take a measure from `docs/weed-hard-rules.md`. Do not
name a cavern measure. Do not invent conquer cuts.

Tests go in `tests/test_piece_border.py`. No Inkscape.
Skip when Qt cannot load.

## Checks

- The inner rectangle is the subject's axis-aligned
  bounds expanded by `inner_distance` on every side. The
  outer rectangle is that rectangle expanded by
  `border_width` on every side. Sides run with the axes.
- An empty subject returns nothing. A path that is not
  passed in does not grow the bounds.
- `pytest tests/test_piece_border.py` passes without
  Inkscape. `src/weedlib/surround/` and
  `src/weedlib/solvers/` are unchanged.

## Note

`piece_border(subject, inner_distance, border_width)` is in
`src/weedlib/piece_border.py` and exported from `weedlib`.
It returns two `QPainterPath` rectangles, inner then outer.
The inner one is the subject's `boundingRect()` expanded by
`inner_distance` on every side. The outer one is that
rectangle expanded by `border_width`. The sides run with
the axes. The lengths are user units, used as given. An
empty subject, including a path that is only a move,
returns `()`. A line still returns the two rectangles. A
path that is not the subject does not grow the bounds, and
a hole does not shrink them. Callers that need one
rectangle unpack the tuple. `()` means there is nothing to
paint or clip.

Why: the clip and the cuts both call this, and the window
paints the paths it is given. This function does not paint,
clip, convert inches, or read a scale.

Checked with `pytest tests/test_piece_border.py`: 8 passed
in 0.05s. No Inkscape. `src/weedlib/surround/` and
`src/weedlib/solvers/` are unchanged.

Summary: No defects. The library returns the inner
rectangle, then the outer one, from the subject's
axis-aligned bounds. The named test passed again. The
surround and the solvers are unchanged.

Context worth keeping: `piece_border(subject,
inner_distance, border_width)` returns two
`QPainterPath` rectangles, or `()` when
`subject.isEmpty()` is true. A path that is only a move
is empty. A line is not. Expansion is
`boundingRect().adjusted` by the length on every side,
then the same for `border_width` on the inner rectangle.
The lengths are user units, used as given. There is no
scale and no inch conversion. A curve uses the drawn
bounds, not the control points. A hole does not shrink
the bounds. A path that is not the argument does not
grow them. Callers that need one rectangle unpack the
tuple. The function does not paint, clip, or call
`generate_weeds`. The pass is `cr-01.md`.

Result: No defects remain. The named checks passed.
`QT_QPA_PLATFORM=offscreen python3 -m pytest
tests/test_piece_border.py`: 8 passed in 0.05s. No
Inkscape. `src/weedlib/surround/` and
`src/weedlib/solvers/` are unchanged. No bug outside
this change.
