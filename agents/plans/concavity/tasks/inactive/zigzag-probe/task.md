# Zig-zag probe

**Status:** done

## Goal

The library returns candidate numbers for one cavern
on one outline. A large zig-zag tooth and a small one
are recorded. No number is the measure.

## Do

Open [`../../../notes.md`](../../../notes.md). This
task says the attempt matters. The kinds there are
examples. The note is not the guide. Do not write a
candidate into the guide.

Add the walk in `src/weedlib/cavern.py`. One outline
in, candidate numbers out. One cavern may produce
more than one number. The walk stays local and
polynomial in that outline. It does not search over
sets of caverns.

Probe a kind from the note when a local walk can
compute it without a mouth. Do not invent a mouth.
Mouth and reach stay two readings. Do not compute
reach squared over reach plus mouth. Skip a kind
that needs that mouth, and say so in the note. Do
not crown a number you did compute.

A rectangle has no cavern to score. A hole loop is
not a cavern, including a concave hole the caller
marks as a hole. Do not decide a hole by searching
the subject. The open piece-border clip is not a
cavern. An open polyline in the test stands in for
that clip. Do not join its ends or score the gap.
Do not build it with the piece border, the surround
builder, or the solver clip.

The picture is a 90-degree zig-zag. Record the
numbers for one large tooth and the same tooth made
small, and which of those numbers change with size.
Do not pick one. Do not add a threshold, and do not
seal either tooth.

Time a short outline and a longer comb of the same
tooth. Record both times in the note. The longer
walk may grow only with the outline. The test does
not encode a time limit. A comb of N teeth yields
one result group per tooth, not one result per pair
of teeth.

Add one index sentence to `src/weedlib/README.md`
and one to `tests/README.md`. Tests go in
`tests/test_cavern.py`. No Inkscape. Do not
re-export the walk from `src/weedlib/__init__.py`.
Do not add a window control.

Do not emit a weed line. Do not change the surround
outline. Do not bridge a mouth. Do not cut a cavern
up. Do not start conquer or the surround coastline.

Do not edit `src/weedlib/solvers/bay.py`. That file
owns island-hop bay seals. Do not edit
`src/weedlib/piece_border.py`,
`src/weedlib/surround/build.py`,
`src/weedlib/solvers/clip.py`, anything else under
`src/weedlib/surround/`, `tests/test_surround_clip.py`,
`tests/test_piece_border.py`, the window or its
tests, `agents/architecture/`, `docs/`,
`agents/plans/piece-border/`, or
`agents/plans/ready-fixes/`. Leave
`tasks/inactive/name-measure/` parked.

## Checks

- The note records the large tooth, the small tooth,
  and both times. It still says none of these is a
  named measure. Both mouth-and-reach readings stay,
  and neither is crowned. A skipped kind says why.
- The large and the small tooth do not return only
  identical numbers. No number is chosen. No
  threshold is added. Nothing is sealed.
- A rectangle, a marked concave hole, and the open
  stand-in produce no cavern. The stand-in was not
  built by the piece border or the surround clip.
- A comb of N teeth is N result groups, not a search
  over sets of teeth. One cavern may produce more
  than one number.
- `pytest tests/test_cavern.py` passes. No Inkscape.
- The guide, the window, the surround package, and
  the other forbidden files are unchanged. No weed
  line. Conquer does not start. `name-measure` stays
  parked.

## Note

Added `src/weedlib/cavern.py`. `probe` takes one
outline and returns the coast length, the total
turn, and the turn per unit length for each
cavern. A caller's hole mark returns nothing. An
open outline does not join its ends. One index
sentence is in each README. The concavity note
records the large tooth, the small tooth, and
both times.

The surround and bay helpers cut turns with
those steps' own cutoffs, so this walk stays on
the outline. These three numbers need no mouth.
The depth-to-mouth ratio needs one, so it is
skipped. Mouth and reach stay two readings.
Reach squared over reach plus mouth is not
computed. No number is crowned. No threshold is
added. Nothing is sealed. Length and the turn
per unit length change with size. The turn does
not.

`python3 -m pytest tests/test_cavern.py`: 6
passed. No Inkscape. The large and the small
tooth are not the same numbers. A rectangle, a
marked concave hole, and the open stand-in
return no cavern. A comb of 5 teeth is 5 groups.

## Summary

`probe` returns coast length, total turn, and turn per
unit length for each cavern on one outline. The large
tooth is length 30, turn pi, and turn per unit length
pi/30. The same tooth at one hundredth is length 0.3,
turn pi, and turn per unit length pi/0.3. Length and
turn per unit length change with size. The turn stays
pi. No number is chosen. The depth-to-mouth ratio is
skipped because this walk does not define a mouth.
Mouth and reach stay two readings. Nothing is sealed.

## Context worth keeping

The glossary names cavern. It does not give mouth or
reach a row. The note keeps both as readings, and the
walk computes neither. Reach squared over reach plus
mouth is not computed. A negative turn groups a concave
run. That sign is not a size threshold. A marked hole
returns before the walk. The open stand-in is a point
list in the test, and its ends are not joined. A comb
of 5 teeth is 5 groups from one pass. The times are in
the note, and the tests do not assert them. `cavern.py`
is 130 lines and stays whole. It is not re-exported.
The guide, the window, the surround package, `bay.py`,
and `propose.py` are not in this diff. `name-measure`
stays parked. The pass is `cr-01.md`.

## Result

No defect. `python3 -m pytest tests/test_cavern.py`:
6 passed in 0.05s. No Inkscape.
