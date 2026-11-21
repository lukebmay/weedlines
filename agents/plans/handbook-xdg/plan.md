# Handbook XDG

**Rank:** 3

## Goal

The job cache follows the XDG directory rule from
catalog 0.9.15. `WEEDLINES_CACHE_HOME`, when set,
is the cache home, with no `/weedlines` suffix.
Otherwise a set `XDG_CACHE_HOME` plus `/weedlines`,
otherwise `~/.cache/weedlines`. Only that resolver
reads `XDG_CACHE_HOME` for this home. Cache is
live: resolve it every run. Do not invent config,
data, state, or runtime homes. Do not move the
Inkscape extensions directory onto a weedlines
home.

## Guide

- [`../../installed/scripting.md`](../../installed/scripting.md)
- [`../../architecture/runtime.md`](../../architecture/runtime.md)
- [`../../architecture/install.md`](../../architecture/install.md)

## Conflict

The runtime part says the cache is
`$XDG_CACHE_HOME/weedlines` when that variable is
set, else `~/.cache/weedlines` on Linux,
`%LOCALAPPDATA%\weedlines\cache` on Windows, and
`~/Library/Caches/weedlines` on macOS.
`extensions/inkscape/weedlines_job.py` reads
`XDG_CACHE_HOME` itself and never reads
`WEEDLINES_CACHE_HOME`.

The installed rule says a set app variable is the
home, and the resolver is the only reader of the
XDG variable. The Windows and macOS defaults are
not that rule. They stay as the runtime part names
them until that part changes.

Changing the runtime sentence asks first. Lay out
this conflict and wait. Do not edit the guide
before the answer. The install part stays: the
extensions directory is Inkscape's, including
`$XDG_CONFIG_HOME/inkscape/extensions` on Linux.
That is the host path, not
`WEEDLINES_CONFIG_HOME`.

## Checks

- A set `WEEDLINES_CACHE_HOME` is the cache
  directory on every platform.
- With that variable unset, Linux stays
  `$XDG_CACHE_HOME/weedlines` or
  `~/.cache/weedlines`. Windows and macOS stay the
  paths the runtime part names.
- `XDG_CACHE_HOME` is read only in that resolver.
- `src/weedlines/install_ext.py` still resolves
  Inkscape's extensions directory.
- Data and state are not recorded at install.
  Runtime is not added.
- The runtime part is edited only after the human
  answers.
