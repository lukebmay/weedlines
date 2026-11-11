# Probes

Open this when the task says the attempt matters. This
note is not the guide. None of these is a named measure.

One old candidate score is reach squared, divided by
reach plus mouth. Mouth and reach were never one
construction. Do not write that score into the guide.

The kinds of number worth probing, as examples only:

- Depth, or the length of the cavern.
- A ratio of that depth to the width of the mouth.
- An angle, as motion past 90 degrees from a starting
  point.
- How quickly the coast becomes concave.

A 90-degree zig-zag is the picture. Large teeth would
need each cave closed. The same teeth, small enough
that the vinyl thickness keeps the waste off the
piece, would not. A probe should show that size
difference as a number. It should stay fast.

## Zig-zag record

`cavern.probe` returns three numbers for each cavern
on one outline. None of these is a named measure.

- Length: the coast through that cavern, from the
  vertex before the first reflex turn through the
  vertex after the last. This is the length kind.
  It is not a depth taken from a mouth.
- Turn: the total right turn along that coast, in
  radians. This is the angle kind.
- Turn per unit length: that turn divided by that
  length. This is how quickly the coast becomes
  concave.

The ratio of depth to the width of the mouth is
skipped. That kind needs a mouth, and this walk does
not define one. Mouth and reach stay two readings.
Neither is crowned. Reach squared over reach plus
mouth is not computed.

Large tooth, in user units. Outline (0, 0), (30, 0),
(30, 20), (18, 20), (18, 8), (12, 8), (12, 20),
(0, 20):

- length 30
- turn pi
- turn per unit length pi/30

The same tooth scaled by 0.01:

- length 0.3
- turn pi
- turn per unit length pi/0.3

Length and turn per unit length change with size.
The turn does not. No number is chosen.

One call on that large tooth, 8 vertices, took
5.98e-6 s. One call on a comb of 200 of the same
tooth, 804 vertices, took 7.09e-4 s. Both are the
mean of repeated calls. The longer walk follows the
outline. The test does not encode a time limit.
