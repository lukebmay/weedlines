# Surround clip

**Status:** done

## Goal

The library clips a surround to the inner rectangle. The
window does not clip it.

## Do

`build_surrounds` in `src/weedlib/surround/build.py`
gains `inner_distance` after `join_gap`. The default
leaves today's paths unchanged, so existing callers keep
working. When `inner_distance` is passed, call
`piece_border` for the inner rectangle and clip to it.
Do not reimplement the rectangle. Do not edit
`src/weedlib/piece_border.py`.

The clip is Surround and Conquer in
`agents/architecture/algorithms.md`. A surround that
meets the inner rectangle is clipped to the inside and
left open. Do not add the inner-rectangle side between
those ends. More than one run follows the same rule.
A surround that stays inside stays closed. A surround
the clip removes entirely is not emitted. Do not cut
the subject. Open ends may sit closer than the surround
distance. The rest of that surround stays at least that
distance away. Do not close the ends. Do not name a
cavern measure. Do not take a measure from
`docs/weed-hard-rules.md`. Do not invent conquer cuts.
Do not remove island-hop.

`build.py` stays one file. Do not add a clip module.
Update the `build.py` sentence in
`src/weedlib/surround/README.md` so it names this clip.
Do not edit the other entries.

Tests go in `tests/test_surround_clip.py`. No Inkscape.
Skip when Qt cannot load. Do not retarget the existing
surround tests. They omit `inner_distance`.

## Checks

- With `inner_distance` omitted, the paths stay as they
  are today.
- Four equal squares set in a rectangle: their outer
  sides are not also the surround. A surround that meets
  the inner rectangle is open, and the side between the
  ends is not part of that path.
- A surround that stays inside stays closed. One the
  clip removes is absent. The subject outline is not a
  new cut.
- `pytest tests/test_surround_clip.py` passes without
  Inkscape. `src/weedlib/piece_border.py` is unchanged.

## Note

`build_surrounds` takes `inner_distance` after `join_gap`.
Omitted, or passed as `None`, the outlines stay as they are
and `piece_border` is not called. When a length is passed,
including zero, `piece_border(subject, inner_distance, 0.0)`
builds the rectangle and only the inner path is used. The
width is not this clip. Each surround is clipped to that
rectangle. A run that meets it is left open, and the
rectangle side between the ends is not part of the path.
More than one run follows the same rule. A surround that
stays inside is returned closed and unchanged. One the
clip removes is absent, and the subject outline is not
put in its place. Join still happens before the clip.
`build.py` stays one file. The `build.py` sentence in
`src/weedlib/surround/README.md` names the clip.
`tests/README.md` has one sentence for
`test_surround_clip.py`.

Why: the outer sides of the subject are the inner
rectangle's cut. The surround must not trace them again.
The open ends are where the surround meets that
rectangle, and they are not moved back out to the
surround distance. The rest of the run stays at least
that distance from the subject.

Checked with `QT_QPA_PLATFORM=offscreen python3 -m pytest
tests/test_surround_clip.py tests/test_surround.py
tests/test_surround_bridge.py tests/test_surround_smooth.py
tests/test_piece_border.py`: 46 passed in 24.92s. No
Inkscape. `src/weedlib/piece_border.py` is unchanged.
`src/weedlib/solvers/` was not edited.

Summary: One defect. The polygon clip matches the rule, and
the named test passed. A distance-0 curve that meets the
inner rectangle is rebuilt from a flattened polygon, and
the chords lie inside the subject.

Context worth keeping: `inner_distance` follows `join_gap`.
Omitted or `None`, the outlines are unchanged and
`piece_border` is not called. A passed length, including
zero, calls `piece_border(subject, inner_distance, 0.0)`
and uses the inner path only. Join, bridge, and smooth
still run first. Island-hop is still there. A polyline
that meets the rectangle stays open, without the rectangle
side between the ends, and the rest stays at the surround
distance. Four squares and a plus do that. A surround that
sits inside stays closed. One the clip removes is absent,
and the subject outline is not put in its place. The
failure is `_clip_surround`: `intersected` still has the
curves, then `toSubpathPolygons()` replaces them with
lines. A circle of diameter 20 at distance 0 and inner
distance 0 becomes a 16-side polygon about 0.20 inside.
A rounded rectangle's corner arcs become lines about 0.12
inside. The pass is `cr-01.md`. The solvers diff is a
different task and was not reviewed.

Result: One defect remains. Do not emit
`toSubpathPolygons()` as the cut. Walk the elements of
`intersected`, keep lines and curves that do not lie on
the inner rectangle, and if nothing was dropped return
the original surround. Add a test the current code fails
for a circle and a rounded rectangle at distance 0 and
inner distance 0. `QT_QPA_PLATFORM=offscreen python3 -m
pytest tests/test_surround_clip.py`: 7 passed in 0.21s.
No Inkscape. `src/weedlib/piece_border.py` is unchanged.

The clip no longer emits `toSubpathPolygons()`. It walks
the lines and curves of `intersected` and drops only an
element that lies on the inner rectangle. If nothing was
dropped, the original surround is returned, curves
included. A circle of diameter 20 at distance 0 and inner
distance 0 stays that closed curve. A rounded rectangle
keeps each corner arc and leaves the flat sides off the
path. Those arcs are not the 0.12-inside chords.

Why: the chords of a flattened curve cut the subject.
The rectangle side is still not part of the run, and the
rest of a run stays at the surround distance.

Checked with `QT_QPA_PLATFORM=offscreen python3 -m pytest
tests/test_surround_clip.py`: 8 passed in 0.22s. No
Inkscape. `src/weedlib/piece_border.py` is unchanged.
`src/weedlib/solvers/` was not edited.

Summary: No defects. The clip walks the lines and curves of
`intersected` and drops only an element that lies on the
inner rectangle. If nothing was dropped, the original
surround is returned. The circle stays that closed curve.
The rounded rectangle keeps its corner arcs. A polyline
run stays open without the rectangle side.

Context worth keeping: `inner_distance` still follows
`join_gap`. Omitted or `None`, `piece_border` is not
called. A passed length, including zero, uses
`piece_border(subject, inner_distance, 0.0)` and the inner
path only. A circle of diameter 20 at distance 0 and inner
distance 0 is the same 13-element curve, samples at radius
10. The rounded rectangle in the test is 40 by 20 with
corner radius 6: four open curves, samples at radius 6,
flat sides left off. Four squares at distance 4 and inner
distance 1 stay four open runs with no rectangle side.
`toSubpathPolygons()` is not the cut. The pass is
`cr-02.md`.

Result: No defects remain. The named check passed.
`QT_QPA_PLATFORM=offscreen python3 -m pytest
tests/test_surround_clip.py`: 8 passed in 0.20s. No
Inkscape. `src/weedlib/piece_border.py` is unchanged.
