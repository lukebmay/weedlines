# Zig-zag probe

**Status:** ready

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

The developer writes what changed, why, and how it was checked.
The reviewer then writes the summary, the context worth keeping,
and the result.
