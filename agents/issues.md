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
| 2026-11-04, `extensions/inkscape/weedlines_dialog.py` | Start for Surround and Conquer still calls `build_surrounds` on the GUI thread. The figure check, the subject and weed area, and the arrow paths now run in a spawned process. Frame, grid, and island-hop already leave Start on a worker. The OS dialog was not reproduced in this turn. | [Run](./architecture/runtime.md). [responsive-run](./plans/responsive-run/plan.md). |
| 2026-11-05, `src/weedlib/solvers.py` | Grid hatch lines are not reported until `grid_weeds` publishes the path after the connected-ends pass. The work-rectangle edges are reported when they are accepted and again at that publish. Confirmed. The progress-check edits did not cause it. | [Run](./architecture/runtime.md). [segment-publish](./plans/segment-publish/plan.md). |

## Closed

| Seen | What happened | Rule |
| --- | --- | --- |
| 2026-11-05, `extensions/inkscape/weedlines_dialog.py` | `test_untouched_apply_returns_the_initial_color` and `test_apply_returns_the_changed_weed_line_color` failed on `d08fccd`. Start on the default Surround and Conquer mode paints a surround and leaves Apply disabled, so the dialog returns `(None, None, None)`. Fixed. The color checks open on frame, which returns cuts. | [Run](./architecture/runtime.md). [_bugs](./plans/_bugs/plan.md). |
| 2026-10-29, `src/weedlib/figures.py`, Qt 5.15.18 | A radius-10 ellipse with a triangular hole whose vertex sits between the curve and a chord (about radius 9.85) returns two self-overlaps. The hole is contained, the outlines do not cross, and the counter is dropped from the subject. The same triangle at radius 9.0 is a counter with no defect. Fixed. The hole stays the counter. | [Self-overlap](./architecture/preflight.md). [_bugs](./plans/_bugs/plan.md). |
| 2026-11-04, `src/weedlib/figures.py` | A radius-10 circle and a radius-3 circle that meet (inner center 7 units out along y=x, within 1e-10) do not keep that hole as the counter. Confirmed and fixed. The hole stays the counter. The inner center is weed area. | [Counter](./architecture/preflight.md). [_bugs](./plans/_bugs/plan.md). |
| 2026-11-04, `src/weedlib/figures.py` | Two figures, a radius-10 circle and a radius-3 circle whose centers are 7 apart along y=x, meet and do not cross. The inner fill lies inside the outer fill. `_overlap_defects` reported one separate-figure overlap at the inner center. Confirmed and fixed. That touch is nesting. | [Separate-figure overlap](./architecture/preflight.md). [_bugs](./plans/_bugs/plan.md). |
| 2026-11-04, `src/weedlib/figures.py` | Two figures, a radius-10 circle and a radius-3 circle whose centers are 12.97 apart along y=x, have outlines that cross. A point near (7.064, 7.064) lies in both fills, and each fill has a point outside the other. `intersected().simplified()` had no area, so the figure check reported no overlap. Distance 12.96 reported one. Distance 13 reported none. Confirmed and fixed. Each shared region is one overlap. | [Separate-figure overlap](./architecture/preflight.md). [_bugs](./plans/_bugs/plan.md). |
