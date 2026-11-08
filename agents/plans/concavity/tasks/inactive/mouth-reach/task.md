# Mouth and reach

**Status:** done

## Goal

Mouth and reach are one construction in the note, or
both readings stay and this task says so. The guide
does not gain a formula.

## Do

Open [`../../../notes.md`](../../../notes.md). The
stage says this task opens it. The note is not the
guide. The candidate score there is not a
construction.

Edit that note only when you can write one
construction of mouth and reach that two
implementers would share. Same outline, same mouth,
same reach. It stays in the note.

Do not pick between the two readings. If you cannot
make one reading, stop and say so in the Note.
Change nothing. Leave both readings. Do not delete
one, crown one, or add a third.

A construction you do write is one length per
cavern. A hole loop is not a cavern. The open
piece-border clip is not a cavern. The walk is
local and polynomial in the outline. It does not
search over sets of caverns. The outline fails on
its worst cavern.

Do not write the formula into the guide or the
library. Do not edit `agents/architecture/`. Do
not emit a weed line, change the surround outline,
or add a control. Do not invent conquer cuts. Do
not name the two piece-border labels. Do not
bridge a mouth. Do not cut a cavern up.

## Checks

- The note has one construction of mouth and reach
  and no second reading, or both readings remain
  and the Note says why one reading was not made.
- A reading was not dropped or crowned while the
  other still fits the note.
- The guide and the library do not name the
  formula. No other file changes.
- No weed line, no surround change, no new
  control, no conquer cut. The two piece-border
  labels are not named.

## Note

One reading was not made. Nothing else changed.
Both readings stay in the candidate note.

They do not name the same mouth. A hull edge of a
reflex run is one segment for that run. The farthest
pair can be one segment across a whole comb. One
score per gap rejects the comb-wide segment. An
inner cavern not added into the outer reach rejects
folding the inner depth into the outer length.
Neither sentence picks the segment list.

The reflex-run sentence is not a shared procedure.
On a rectangular tube the hull of the reflex
vertices is the floor, already a polyline edge, so
that reading has no mouth. A long tube scores
toward its reach, so another implementer includes
the shoulders and does get a mouth. The sentence
does not say which.

A bay with a cavern in its floor keeps the fork
after shoulders are included. Each reflex run can
close on its own, and the bay mouth is never
emitted, so the bay reach is not the outer length.
A mouth across the bay keeps that outer length
only by spanning more than one run, which is the
comb reading. One outline cannot take both mouths
without another rule, and it cannot take one of
them without crowning the other.

Reach splits the same way. Distance from the mouth
stays small on a shallow bay. The farthest pair in
that bay is about as wide as the mouth, so the
score would not stay small. The note still lets
that pair be read as the mouth.

A local walk does not remove the fork. A search
over sets of caverns is not allowed. A hole loop
is not a cavern, and the open piece-border clip
is not a cavern. Neither reading says so, and
saying so does not make the mouths match.

Checked the candidate note still has both readings
and no construction. The guide and the library
were not edited. No weed line, no surround change,
no new control, no conquer cut. The two
piece-border labels were not named.

Summary: No defect. One reading was not made. Both
readings stay in the candidate note. The task note
is the only edit. There is no automated test.

Context worth keeping: The two readings still do
not name the same mouth. A hull edge of a reflex
run is one segment for that run. The farthest pair
can be one segment across a whole comb. On a
rectangular tube the first reading has no mouth
when that hull edge is already a polyline edge. A
long tube that scores toward its reach can include
the shoulders and get a mouth. A bay with a cavern
in its floor keeps that fork. Distance from the
mouth stays small on a shallow bay, while the
farthest pair there is about as wide as the mouth.
A local walk does not remove the fork. The
candidate score is not a construction, and the
guide still does not name it. `name-measure` stays
waiting on two readings. The pass is `cr-01.md`.

Result: No defect. The stop matches the task.
`git diff` has no hunk for the candidate note.
The architecture diff does not add the score or
either reading, and those files were already
dirty before this note. `git status` for the
library, the tests, the extension, and the docs
is empty. There is no automated test.
