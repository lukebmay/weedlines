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
| 2026-10-29, `src/weedlib/figures.py`, Qt 5.15.18 | A radius-10 ellipse with a triangular hole whose vertex sits between the curve and a chord (about radius 9.85) returns two self-overlaps. The hole is contained, the outlines do not cross, and the counter is dropped from the subject. The same triangle at radius 9.0 is a counter with no defect. | [Self-overlap](./architecture/preflight.md). [_bugs](./plans/_bugs/plan.md). |
