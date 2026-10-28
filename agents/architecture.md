# Architecture

When to use: Which product part. Open this index, then the one
part the task names.

**Owner:** human. Agents may propose edits; apply only with explicit permission.

This file is the index of the guide: how the product is supposed
to work, including the vision that the code has not reached yet.
It records what has worked and warns about what has failed. It
is not a snapshot of today's tree, not a log of bugs, and not a
ban on a better design. Bugs live in [`issues.md`](./issues.md).

Each part of the guide lives in one file under
[`architecture/`](./architecture/). This file says how those
parts fit and which file to open. It does not restate a part.
When `architecture/` does not exist yet, this file is the whole
guide until the parts are split out.

The orchestrator reads this index and every part file. That rule
is [`roles/orchestrator.md`](roles/orchestrator.md). Another agent
opens this index and the one part the task names.

Product words: [`architecture/glossary.md`](./architecture/glossary.md).
Handbook words: [`glossary.md`](./glossary.md). When work is complete:
[`acceptance.md`](./acceptance.md). How work is run is
[`handbook.md`](handbook.md). Stone is the stone row in
[`glossary.md`](./glossary.md).

Gaps between this guide and the running code are closed with a plan.
Do not rewrite the guide to describe leftovers.

## This file can be wrong

This file is what we **currently believe**. It is not a proof. It
will change. An old sentence is not kept because it is old. The
same rule covers every file under `architecture/`.

A better design is welcome. Bring it to the orchestrator with the
argument. If a sentence in this guide is **directionally wrong** (the
structure or the product intent, not a leftover in the code),
**stop work on that issue**. Do not paper over it with a second
path. Do not silently edit the guide. Do not silently change the
code to match a sentence you suspect is stale. We meet. Write the
new sentence in the part it belongs to only when the human says to:
what is true, who does it, and what it does not cover. One sentence
of why when the choice is easy to undo the wrong way. Do not write
what was rejected, and do not record the incident.

**Why this paragraph exists:** agents treated this file as
unchangeable, then hid misses behind fallbacks.

Code that merely lags this guide is a plan, not a meeting. A meeting
is for when the guide itself looks like the mistake.

## What is being built

Weedlines is an Inkscape extension plus a geometry library. The
person selects a design, the extension opens a window, and the
window shows a live preview. An algorithm then emits weed lines:
cuts that let the person peel waste vinyl away from the design.

Three layers do this work. The host talks to Inkscape. The window
shows the preview and takes the person's choices. The library
classifies the design and emits weed lines. One layer does not do
another layer's job.

Every algorithm waits on the same figure check. Surround and
Conquer is one of those algorithms. Its cut subroutines are not
specified yet. The check, the preview, and the way correction
arrows go back to Inkscape are specified, and they apply to every
algorithm.

Frame stays the default mode. Island-hop does not become the
default until its pictures are accepted. This repo stays the
home of the solvers.

## How the parts fit

A run moves in this order.

1. The host reads the selection and writes a job. The job still
   has each path, its computed fill, and the document size.
2. The window loads the job. It asks the library for the figure
   check, the subject, and the weed area.
3. The window paints the preview. When the check finds a defect,
   the window offers the two return actions under the preview.
4. When the check is clear, the person can start frame, grid, or
   island-hop. The library emits weed lines. The window paints
   them in the weed-line color. Surround and Conquer is not a
   choice until its subroutines exist.
5. Import reads the result file. A weed-line result brings in a
   copy of the design and the cuts. A correction-arrow result
   brings in only the arrow groups, above the open document.

| Piece | Owns | Must not own |
| --- | --- | --- |
| Host | The selection, the job, the result files, and import into the document | Figure classification, weed-line geometry |
| Window | The preview, the plugin settings, swap, and the start and return actions | Path topology, solver cuts |
| Library | Figures, subject and weed area, the figure check, arrow paths, and the algorithms | The Inkscape document, widgets |
| Surround and Conquer | Its cut subroutines, once they are specified | The figure check and the other modes |

## Which file

Put the rules for a part in `architecture/<part>.md`. Put key
inner workings there too. This index only points.

| When the task is about | Read |
| --- | --- |
| A product word | [`architecture/glossary.md`](./architecture/glossary.md) |
| Figures, dangling ends, overlap, the gate | [`architecture/preflight.md`](./architecture/preflight.md) |
| Preview paint, swap, arrows, return actions | [`architecture/preview.md`](./architecture/preview.md) |
| The job, the result, import | [`architecture/host.md`](./architecture/host.md) |
| Frame, grid, island-hop, Surround and Conquer | [`architecture/algorithms.md`](./architecture/algorithms.md) |
| Pause, cancel, logging, the cache | [`architecture/runtime.md`](./architecture/runtime.md) |
| Install and update | [`architecture/install.md`](./architecture/install.md) |
| SVG conversion, the Qt binding, or units | [`architecture/boundary.md`](./architecture/boundary.md) |
