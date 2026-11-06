# Seal report

**Status:** ready

## Goal

Each island-hop seal is reported once. The path the mode
returns stays the same. If the double report cannot be
confirmed, the task closes with no code change.

## Do

A reviewer reported this. Confirm it before changing code.
Two 30 by 20 rectangles at (0, 0) and (50, 0), padding 10,
collar 4. The report says the path has 19 segments and the
hook receives 21. `(30, 0)–(50, 0)` comes from both
`_add_seg` calls in `_agglomerate_islands`.
`(30, 20)–(50, 20)` comes from both `_add_seg` calls in
`_seal_frame_peninsulas`. One call writes the weed path.
The other writes the `seen` copy. The returned path has
each once.

If that case does not report a segment twice, stop. Say
what the hook received. Do not change code.

If it does, report each of those seals once. Do not change
the path island-hop returns. Do not report from inside
`_add_line_segs`. Do not change the hole-split report,
`grid_weeds`, or `frame_weeds`. Do not edit the window or
`src/weedlib/progress.py`.

## Checks

`pytest tests/test_progress.py tests/test_weeds.py` with
no Inkscape.

- On that two-rectangle case, the hook receives each seal
  once, and the returned path is unchanged.
- The hole-split check still receives its two splits once.
- The island-hop paths locked in `tests/test_weeds.py`
  still match.

## Note

The developer writes what changed, why, and how it was checked.
The reviewer then writes the summary, the context worth keeping,
and the result.
