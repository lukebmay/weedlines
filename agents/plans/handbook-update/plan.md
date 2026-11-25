# Handbook update

**Rank:** 3

## Goal

The installed catalog is 0.9.20. It was 0.9.19.
A later agent brings this repo in line with
`agent-handbook changelog 0.9.19`. That command
prints 0.9.19 and every newer heading. A newer
entry replaces an older one on the same rule. Do
not copy the changelog. This plan does not make
those product edits.

## Guide

- [`../../handbook.md`](../../handbook.md)

## Range

0.9.20 changes how an accepted plan writes the
guide, adds Clarity, names the developer as the
senior developer, and adds the regression role.

The code does not say the installed command runs
from the checkout. No product correction was filed
for 0.9.20.

`agents/architecture.md` still says "Opening a plan
does not write this file." `agents/acceptance.md`
still says "before or with the plan." Those files
are not the blank seed. This plan does not edit
them, and it does not open a handbook plan to edit
them.

## Plans already here

Left: [handbook-xdg](../handbook-xdg/plan.md). It
waits on the human for the runtime sentences. The
guide was not edited. It stays at rank 5. It was
already on the queue. This update does not add it
again.

Dropped: none.

No other active plan's instructions disagree with
the installed handbook. None were rewritten.

## Topic plans

Not added to [`../../priority.md`](../../priority.md):

- This update opened no `handbook-<topic>` plan.
  [handbook-xdg](../handbook-xdg/plan.md) remains
  the earlier correction.

## Checks

- The catalog version in this plan is 0.9.19, then
  0.9.20.
- `agent-handbook update` refreshed documentation
  and scripting. Nothing moved out of
  `agents/installed/`. Root `AGENTS.md` was left
  unchanged. `agents.py` was not restored.
- Product code is not edited from this plan.
- This plan stays off the queue unless a later
  message adds it.
