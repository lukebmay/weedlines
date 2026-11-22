# Handbook update

**Rank:** 3

## Goal

The installed catalog is 0.9.19. It was 0.9.18.
A later agent brings this repo in line with
`agent-handbook changelog 0.9.18`. That command
prints 0.9.18 and every newer heading. A newer
entry replaces an older one on the same rule. Skip
the older entry. This plan does not make those
product edits.

## Guide

- [`../../handbook.md`](../../handbook.md)
- [`../../installed/scripting.md`](../../installed/scripting.md)

## Range

0.9.19 replaces the 0.9.15 XDG home rule. The
statement is "XDG directory variables" in
scripting 2.10.0. Any app or script that keeps
config, data, state, cache, logs, or runtime
files uses those homes, including a program that
is not installed. There is no detector for a
missing XDG system, no `~/.<app>/` default,
runtime does not fall back to `/tmp`, and logs
stay in the state home. A program with no install
record resolves data and state on each run.
0.9.18 is the handbook-update shape. It is
already in [`../../handbook.md`](../../handbook.md).

## Plans already here

Rewritten: [handbook-xdg](../handbook-xdg/plan.md).
It now follows scripting 2.10.0. The cache
resolver stays. Logs in the cache, and the
platform cache defaults, wait on the runtime
sentences. It stays at rank 5. It was already on
the queue. This update does not add it again.

Dropped: none.

No other plan's instructions disagree. No plan
tells an agent to detect an XDG system, to use
`~/.weedlines`, or to put runtime files in
`/tmp`.

## Topic plans

Not added to [`../../priority.md`](../../priority.md):

- [handbook-xdg](../handbook-xdg/plan.md) — `host.log`
  and `ready.log` still go to the cache directory,
  and the unset cache path is still the runtime
  part's Windows and macOS directories. No second
  homes plan.

`~/.ssh` and `~/.gitconfig` are not this rule.
Inkscape's extensions directory is the host path.
That read of `XDG_CONFIG_HOME` is not a weedlines
config home.

## Checks

- The catalog version in this plan is 0.9.18, then
  0.9.19.
- Product code is not edited from this plan.
- This plan stays off the queue unless a later
  message adds it.
