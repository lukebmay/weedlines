# Handbook XDG

**Rank:** 5

## Goal

Weedlines keeps a cache and logs. It has no install
record. Those homes follow the XDG directory rule in
scripting 2.10.0, catalog 0.9.19, which replaces
0.9.15. A set app variable is that home, with no
`/weedlines` suffix. Otherwise a set XDG variable
plus `/weedlines`, otherwise the spec default plus
`/weedlines`. Unset XDG variables are the normal
case. Do not test for an XDG system. Do not use
`~/.weedlines`. Cache is live. Logs stay in the
state home. There is no log variable. With no
install record, state is resolved on each run. Do
not create an install record only to hold that
path. Runtime is not kept. Do not add it, and do
not use `/tmp`. Do not invent a config or data
home. Do not move the Inkscape extensions directory
onto a weedlines home. `~/.ssh` and `~/.gitconfig`
are not this rule.

The cache resolver is already in. This plan does
not redo that task. It does not make the product
edits below until the human answers the runtime
sentences.

## Guide

- [`../../installed/scripting.md`](../../installed/scripting.md)
- [`../../architecture/runtime.md`](../../architecture/runtime.md)
- [`../../architecture/install.md`](../../architecture/install.md)

## Conflict

The runtime part says the cache is
`$XDG_CACHE_HOME/weedlines` when that variable is
set, else `~/.cache/weedlines` on Linux,
`%LOCALAPPDATA%\weedlines\cache` on Windows, and
`~/Library/Caches/weedlines` on macOS. It does not
name `WEEDLINES_CACHE_HOME`. It also says the
detached window's stdout and stderr go to
`host.log` in that cache directory.

`cache_dir` in
`extensions/inkscape/weedlines_job.py` already
reads `WEEDLINES_CACHE_HOME` on every call. A
non-empty value is the directory. Otherwise it
still uses the platform paths that sentence names,
including when both cache variables are unset.
`spawn_detached` writes `host.log` and `ready.log`
into that cache directory. The installed rule puts
logs in the state home, and the unset cache default
is `$HOME/.cache/weedlines` on every platform.

Changing those runtime sentences asks first. Lay
out this conflict and wait. Do not edit the guide
before the answer. Do not move the logs, and do
not replace the Windows and macOS cache branches,
before that answer.

The install part stays. The extensions directory
is Inkscape's, including
`$XDG_CONFIG_HOME/inkscape/extensions` on Linux.
The read in `src/weedlines/install_ext.py` is the
host path, not `WEEDLINES_CONFIG_HOME`.

## Checks

- A non-empty `WEEDLINES_CACHE_HOME` is the cache
  directory. `XDG_CACHE_HOME` is read only in
  `cache_dir`.
- When both cache variables are unset, the spec
  default is `$HOME/.cache/weedlines`. The code
  and the runtime sentence still name the Windows
  and macOS paths. They stay until the human
  answers.
- `host.log` and `ready.log` belong in the state
  home, resolved each run: a set
  `WEEDLINES_STATE_HOME`, else
  `$XDG_STATE_HOME/weedlines`, else
  `$HOME/.local/state/weedlines`. No install
  record is created for that path. They stay in
  the cache directory until the human answers.
- No config, data, or runtime home is added.
  Runtime does not fall back to `/tmp`.
- `inkscape_extensions_dir` still resolves
  Inkscape's extensions directory.
- The runtime part is edited only after the human
  answers.
