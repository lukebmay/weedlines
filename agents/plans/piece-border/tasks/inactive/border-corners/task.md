# Border corners

**Status:** done

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

`piece_border(subject, inner_distance, border_width, corner_radius=None)`
rounds every corner of both rectangles when `corner_radius` is
set. Omitted, `None`, zero, or below stays the square rectangles
the library already emits. The same capped radius is used on both.
The cap is half the shorter side of the inner rectangle, so a
larger value is not used and the arcs stay circular. The radius is
user units; this function does not read a scale.

`build_surrounds` and `generate_weeds` take the same optional
argument and pass it only when the caller set it. Callers that
pass the two lengths alone, including the window ask, stay on
today's square borders and today's clips. The surround clip and
the solver clip follow the inner path. A rounded corner is not
clipped to the bounding box. The border width is still not the
clip. The outer border is still added after the clip and is still
the only cut outside the inner border. Open surround ends are not
closed. Island-hop still runs.

Why: both rectangles and both clips have to share one inner
border. A square clip would keep the corner cutout, which is
inside the box and outside the arc.

Checked with `python3 -m pytest tests/test_piece_border.py
tests/test_surround_clip.py tests/test_border_cuts.py`: 36
passed. No Inkscape. Also `tests/test_frame.py` and
`tests/test_progress.py`: 19 passed, 2 skipped. The rounded
subject fixture in `tests/test_surround_clip.py` still passes.

The window does not pass `corner_radius` yet.
`extensions/inkscape/weedlines_dialog/geometry_ask.py` still calls
`piece_border`, `build_surrounds`, and `generate_weeds` without
it. That file was left alone.

Summary: No defect in this change. Omitted, `None`, zero,
or below stays the square rectangles and the square clips.
A larger radius is capped at half the shorter side of the
inner rectangle, and both rectangles use that radius. The
surround clip and the solver clip follow the inner path,
not the bounding box. The border width is not the clip.
Open ends stay open. Island-hop still runs. Flattening
runs only when the published path already has a curve, so
a square border with no radius still publishes the cuts
that were already accepted. `emit.py` is 764 lines. The
new lines are still the publish clip. No split.

The window ask is a real gap, and it is not a defect in
this change. `geometry_ask.py` still calls `piece_border`,
`build_surrounds`, and `generate_weeds` without
`corner_radius`. `_ask_border` and `_ask_surrounds` in
that file, and `_solver_request` in
`extensions/inkscape/weedlines_dialog/run_controls.py`,
do not send a radius. The form task
`tasks/inactive/border-options/task.md` may edit `form.py`
only, and it must not build or clip the rectangles. It
can show the control and trigger today's ask. It is not
allowed to forward the radius.

Context worth keeping: Callers that pass only the two
lengths are unchanged, including the window ask and the
rounded-subject fixture in `tests/test_surround_clip.py`.
The surround clip still calls `piece_border` with border
width `0.0` and uses the inner path. The outer border is
still added after the solver clip. The form and the guide
were not edited. The pass is `cr-01.md`.

Result: No defect. `python3 -m pytest tests/test_piece_border.py
tests/test_surround_clip.py tests/test_border_cuts.py`:
36 passed in 0.78s. `python3 -m pytest tests/test_frame.py
tests/test_progress.py`: 19 passed, 2 skipped, in 3.21s.
The skips are the two Inkcut job-pipeline tests in
`tests/test_frame.py`. No Inkscape. The ask gap is
confirmed and was not fixed.
