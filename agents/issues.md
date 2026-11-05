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
| 2026-11-04, `src/weedlib/figures.py` | Two figures, a radius-10 circle and a radius-3 circle whose centers are 12.97 apart along y=x, have outlines that cross. A point near (7.064, 7.064) lies in both fills, and each fill has a point outside the other. `intersected().simplified()` in `_overlap_defects` has no area, and the function returns before the outline test, so the figure check reports no separate-figure overlap. Distance 12.96 reports one. Distance 13 reports none. The review reported this. A second agent has not confirmed it. | [Separate-figure overlap](./architecture/preflight.md). [_bugs](./plans/_bugs/plan.md). |

## Closed

| Seen | What happened | Rule |
| --- | --- | --- |
| 2026-10-29, `src/weedlib/figures.py`, Qt 5.15.18 | A radius-10 ellipse with a triangular hole whose vertex sits between the curve and a chord (about radius 9.85) returns two self-overlaps. The hole is contained, the outlines do not cross, and the counter is dropped from the subject. The same triangle at radius 9.0 is a counter with no defect. Fixed. The hole stays the counter. | [Self-overlap](./architecture/preflight.md). [_bugs](./plans/_bugs/plan.md). |
| 2026-11-04, `src/weedlib/figures.py` | A radius-10 circle and a radius-3 circle that meet (inner center 7 units out along y=x, within 1e-10) do not keep that hole as the counter. Confirmed and fixed. The hole stays the counter. The inner center is weed area. | [Counter](./architecture/preflight.md). [_bugs](./plans/_bugs/plan.md). |
| 2026-11-04, `src/weedlib/figures.py` | Two figures, a radius-10 circle and a radius-3 circle whose centers are 7 apart along y=x, meet and do not cross. The inner fill lies inside the outer fill. `_overlap_defects` reported one separate-figure overlap at the inner center. Confirmed and fixed. That touch is nesting. | [Separate-figure overlap](./architecture/preflight.md). [_bugs](./plans/_bugs/plan.md). |
