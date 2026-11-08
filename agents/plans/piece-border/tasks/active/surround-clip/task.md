# Surround clip

**Status:** ready

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

The developer writes what changed, why, and how it was checked.
The reviewer then writes the summary, the context worth keeping,
and the result.
