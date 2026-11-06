---
title: Issues
read_when: Filing a bug, reading a known miss, or about to put a bug story into architecture
order: 40
---

# Issues

**Owner:** agent. Agents read and write this file.

Bugs live here. They are not stone, and they are not the design.
How the product is built stays in [`architecture.md`](./architecture.md).
A product check stays in [`acceptance.md`](./acceptance.md). A fix
still needs a test ([`testing.md`](./testing.md)). Closing a row
does not replace that test.

A new miss gets a row under **Open** in the same turn it is found.
When a row would change the target design, stop and meet. Do not
paper the architecture with the story.

## Open

| Seen | What happened | Rule |
| --- | --- | --- |

## Closed

| Seen | What happened | Rule |
| --- | --- | --- |
| 2026-11-05, `src/weedlib/solvers.py` | Some island-hop seals were reported twice. Two 30 by 20 rectangles at (0, 0) and (50, 0), padding 10, collar 4, returned 19 segments and the hook received 21. Fixed. The `seen` copy does not report. The weed-path call still does. The path still has each seal once. | [Run](./architecture/runtime.md). [_bugs](./plans/_bugs/plan.md). |
| 2026-11-05, `src/weedlib/solvers.py` | Island-hop hole splits were returned as weed lines and never reached the geometry hook. Fixed. The splits path is reported at the add, before the hug pass. On a 200 by 160 frame with a 180 by 140 hole, the hook receives the two splits once each, and the path still returns them. | [Run](./architecture/runtime.md). [island-segments](./plans/island-segments/plan.md). |
| 2026-11-05, `src/weedlib/solvers.py` | Grid hatch lines were reported only when the finished path was published, so work-rectangle edges were reported again. Fixed. Hatch is reported when `_grid_in_region` returns, before connected-ends. Each work-rectangle edge is reported once. | [Run](./architecture/runtime.md). [segment-publish](./plans/segment-publish/plan.md). |
| 2026-11-05, `tests/test_window_timing.py` | `test_hold_on_a_thread_blocks_the_gui_timer` failed when `processEvents` returned before the worker entered the non-yielding loop. The assert saw about 0 instead of more than 0.05. Fixed. The worker waits until just before `processEvents`, and that call has to both deliver the timer and take more than 0.05s. An immediate hold still fails. | [Run](./architecture/runtime.md). [_bugs](./plans/_bugs/plan.md). |
| 2026-11-04, `extensions/inkscape/weedlines_dialog.py` | The figure check, the surround, and frame, grid, and island-hop ran on the GUI thread or on a thread in that process, so the window could not paint. Fixed. They run in the spawned geometry process. Close does not join that work. The OS dialog was not reproduced. | [Run](./architecture/runtime.md). [responsive-run](./plans/responsive-run/plan.md). |
| 2026-11-05, `extensions/inkscape/weedlines_dialog.py` | `test_untouched_apply_returns_the_initial_color` and `test_apply_returns_the_changed_weed_line_color` failed on `d08fccd`. Start on the default Surround and Conquer mode paints a surround and leaves Apply disabled, so the dialog returns `(None, None, None)`. Fixed. The color checks open on frame, which returns cuts. | [Run](./architecture/runtime.md). [_bugs](./plans/_bugs/plan.md). |
| 2026-10-29, `src/weedlib/figures.py`, Qt 5.15.18 | A radius-10 ellipse with a triangular hole whose vertex sits between the curve and a chord (about radius 9.85) returns two self-overlaps. The hole is contained, the outlines do not cross, and the counter is dropped from the subject. The same triangle at radius 9.0 is a counter with no defect. Fixed. The hole stays the counter. | [Self-overlap](./architecture/preflight.md). [_bugs](./plans/_bugs/plan.md). |
| 2026-11-04, `src/weedlib/figures.py` | A radius-10 circle and a radius-3 circle that meet (inner center 7 units out along y=x, within 1e-10) do not keep that hole as the counter. Confirmed and fixed. The hole stays the counter. The inner center is weed area. | [Counter](./architecture/preflight.md). [_bugs](./plans/_bugs/plan.md). |
| 2026-11-04, `src/weedlib/figures.py` | Two figures, a radius-10 circle and a radius-3 circle whose centers are 7 apart along y=x, meet and do not cross. The inner fill lies inside the outer fill. `_overlap_defects` reported one separate-figure overlap at the inner center. Confirmed and fixed. That touch is nesting. | [Separate-figure overlap](./architecture/preflight.md). [_bugs](./plans/_bugs/plan.md). |
| 2026-11-04, `src/weedlib/figures.py` | Two figures, a radius-10 circle and a radius-3 circle whose centers are 12.97 apart along y=x, have outlines that cross. A point near (7.064, 7.064) lies in both fills, and each fill has a point outside the other. `intersected().simplified()` had no area, so the figure check reported no overlap. Distance 12.96 reported one. Distance 13 reported none. Confirmed and fixed. Each shared region is one overlap. | [Separate-figure overlap](./architecture/preflight.md). [_bugs](./plans/_bugs/plan.md). |
