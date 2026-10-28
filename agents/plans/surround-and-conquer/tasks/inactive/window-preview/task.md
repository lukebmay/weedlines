# Window preview

**Status:** done

## Goal

The window paints the subject, the weed area, and the library's
arrows. Swap and the four color controls only change that paint.

## Do

- Edit `extensions/inkscape/weedlines_dialog.py` only.
- Paint the library regions and the paths from `build_arrow_paths`.
  Do not invent a second set of arrows. Do not reimplement
  topology.
- Weed lines use the weed-line color, on top of the checkerboard.
  After cuts exist, the checkerboard also covers the work region
  that mode already cuts. Do not change how the solver computes
  that region.
- Swap and the four plugin settings are the controls in
  `agents/architecture/preview.md`. They sit in the form above the
  preview. After either change, ask the library again and repaint.
  Do not store the colors in a preferences file.
- Leave the Start gate as the window-gate task left it. Do not add
  Surround and Conquer. Do not add the return line.
- Tests go in `tests/test_window_preview.py`. Offscreen when Qt
  loads. Skip when Qt cannot load. No Inkscape.

## Checks

- A solid subject paints in its fill. A subject with no paint, or
  with other paint, uses the default subject color. Weed area uses
  the two checkerboard colors. The view background outside that
  area is unchanged.
- Weed lines use the weed-line color, not the old orange pen.
- Preview arrows are the paths `build_arrow_paths` returns, in the
  three arrow colors.
- One swap control exchanges the regions, and the next press
  restores them. The four color controls change paint only. Their
  initial colors are the Paint table in the preview part.
- Start stays disabled when the check reports a defect.
- `pytest tests/test_window_preview.py` passes offscreen, or skips
  only because Qt is missing.

## Note

The preview paints the library subject and weed area, and the
paths from `build_arrow_paths`, instead of a blue subject outline
and the old orange cut pen. A solid `#rrggbb` fill is painted in
that color. A subject with no paint, or with other paint, uses
the default subject color. The weed area is a checkerboard of the
two checkerboard colors. The view background outside that area is
unchanged. Once cuts exist, the checkerboard also covers
`padded_work_rect` for the keep and padding of that run. Subject
paint sits above that rect. Weed lines use the weed-line color.

Swap is one button, "Swap subject and weed area", in the form
above the preview. Each press calls `subject_weed_regions` with
the flag flipped, and the next press restores the first
assignment. The four color fields are in that same form. Their
initial colors are the Paint table. They are not stored in a
preferences file. After a swap or a color change, the window asks
the library again and repaints. Those controls do not change the
figure check. Start stays disabled while that check reports a
defect. The mode list is still frame, grid, and island-hop. There
is no return line. Solvers were not edited.

Checked with `QT_QPA_PLATFORM=offscreen pytest
tests/test_window_preview.py`: 5 passed. Also
`QT_QPA_PLATFORM=offscreen pytest tests/test_window_gate.py`:
9 passed. Qt loaded. The new tests do not load Inkscape.

Review summary: one defect remains. The preview asks
`subject_weed_regions` and paints the paths from
`build_arrow_paths`. The four initial colors are the Paint
table. Swap exchanges the regions, and the next press restores
them. Weed lines use the weed-line color, not `#e07020`. Start
stays disabled while the check reports a defect. There is no
return line. A solid self-overlapping figure paints the crossing
lens in the default subject color. The odd-even fill of
`figure.path` drops that lens, and the library still counts it
as subject. The two squares in the arrow fixture, fill
`#222222`, render the arm (102, 102) as `#222222` and the lens
(107.5, 107.5) as `#ffffff`.

Context worth keeping: `blocked` is `bool(check.defects)`. The
new Start test uses one open path. Swap before Start passes the
swapped subject into `generate_weeds`. Swap after Start does not
rerun the solver. The work rect stays `padded_work_rect` of the
keep and padding captured at Start. Colors live on the edits,
not in a preferences file. The pass is `cr-01.md`.

Result: one defect remains. The suite passed.
`QT_QPA_PLATFORM=offscreen pytest tests/test_window_preview.py
tests/test_window_gate.py` passed (14 passed, no skips). Qt
loaded. Island-hop ran. The new tests do not load Inkscape.
Remedy: paint a solid figure from the painted interior
`subject_weed_regions` unions (`_painted_parts` on that figure's
subpaths), then intersect it with the current subject. Do not
odd-even `figure.path`, and do not copy that interior into the
dialog. Add a test that the lens is the fill, not `#ffffff`.

A solid figure is no longer an odd-even fill of `figure.path`.
The overlay is `_painted_parts` on that figure's subpaths,
intersected with the current subject. The crossing lens stays
filled. The dialog does not copy that interior. Solvers were not
edited. There is no return line.
`test_solid_self_overlap_paints_the_crossing_lens` samples the
arrow fixture: the arm at (102, 102) and the lens at
(107.5, 107.5) are both `#222222`.

Checked with `QT_QPA_PLATFORM=offscreen pytest
tests/test_window_preview.py tests/test_window_gate.py`: 15
passed. Qt loaded. The tests do not load Inkscape.

Review summary: no defects remain. A solid figure is no longer
an odd-even fill of `figure.path`. The overlay is
`_painted_parts` on that figure's subpaths, intersected with the
current subject, then filled in the figure's `#rrggbb`. The
dialog does not copy that interior. The crossing lens paints in
the fill. Swap clears that overlay, and the next press restores
it. The rest of the preview is unchanged. Solvers were not
edited. There is no return line.

Context worth keeping: `test_solid_self_overlap_paints_the_crossing_lens`
samples the arrow fixture, fill `#222222`. The arm at (102, 102)
and the lens at (107.5, 107.5) are both `#222222`. Odd-even of
`figure.path` leaves the lens `#ffffff` and fails that test. The
lens point also lies in the first square; the locked failure is
the double-covered lens. A separate render, not a suite test,
showed the second square at (112, 112) and the lens corners as
`#222222`. After one swap those points are checkerboard
`#e6e6e6`, and a gap at (101, 112) is `#ffffff`. The next press
restores the fill. `contains` on the intersected part agrees.
The self-overlap arrow covers (113, 108) as `#00e5ff`. The suite
points do not. The pass is `cr-02.md`.

Result: no defects remain. The suite passed.
`QT_QPA_PLATFORM=offscreen pytest tests/test_window_preview.py
tests/test_window_gate.py` passed (15 passed, no skips). Qt
loaded. Island-hop ran. The tests do not load Inkscape.
`src/weedlib/solvers.py` and `src/weedlib/figures.py` have no
diff.
