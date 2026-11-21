# Handbook update

**Rank:** 3

## Goal

The installed catalog is 0.9.18. It was 0.9.15.
A later agent brings this repo in line with
`agent-handbook changelog 0.9.15`. That command
prints 0.9.15 and every newer heading. A newer
entry replaces an older one on the same rule. Skip
the older entry. This plan does not make those
product edits.

This is the first handbook-update here. Plans
opened before catalog 0.9.18 may omit the
`handbook-` prefix. They were found by what they
change, not by that prefix.

## Guide

- [`../../../handbook.md`](../../../handbook.md)
- [`../../../installed/scripting.md`](../../../installed/scripting.md)

## Range

0.9.18 is this plan. Code that lags is a
`handbook-<topic>` plan. Related corrections share
one plan. 0.9.17 replaces the one-file count from
0.9.16: a program that is one source file, and a
script that is the whole program, stays one file
until 5000 lines. Do not use a 3000 line count.
0.9.16 aims an ordinary source file under 1200
lines. 0.9.15 is the app directory resolver.

## Plans already here

Rewritten: [source-split](../../source-split/plan.md).
The size bar is 1200 lines, not 1000. The stage no
longer cites a 500-line ceiling. The named small
files stay whole. It stays on the queue. The split
stage is met. No open task. It is a real split of
multi-file modules that were over 1200 lines.
`solvers.py` was thousands of lines. It is not a
one-file program or a whole-program script under
5000 lines. Completed task notes still say 1000
lines. That is the bar that pass checked. It is
not the current rule.

Dropped off the queue: none.

No other plan's instructions disagree. No plan
splits `install`, `scripts/install.py`, or another
one-file program under 5000 lines.

## Topic plans

- [handbook-xdg](../../handbook-xdg/plan.md) — the job
  cache does not read `WEEDLINES_CACHE_HOME`. A
  later message queued it at rank 5.

Nothing else lags. No product source file or test
is over 1200 lines. The longest is
`tests/test_window_gate.py` at 982. Inkscape's
extensions directory stays the host path. That
read of `XDG_CONFIG_HOME` is not a weedlines
config home, so it is not a second topic.

## Checks

- The catalog version in this plan is 0.9.15, then
  0.9.18.
- Product code is not edited from this plan.
- This record stays off the queue. `handbook-xdg`
  is queued.
