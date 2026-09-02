---
title: Scripting
read_when: Writing or changing shell/Python scripts, installers, CLI tools, bin entries, or launching user-visible apps from a Grok agent
order: 40
---

# Scripting

Assume **Linux** (Ubuntu LTS unless stated). Prefer portable choices when cheap.

Language style: `agents/languages/<lang>.md` when relevant. In-repo formatter/LSP wins.

## Scripts → `bin/`

`installer/build-scripts.py` flattens tools into `$shellrc/bin/`.

| Kind | How |
| --- | --- |
| Standalone | `scripts/foo.zsh` → `bin/foo` |
| Multi-file | Package markers; only entry lands in `bin/` |

Do not treat a shebang alone as “this is a bin entry.” See `agents/scripts-build.md` when present.

## All scripts

- Hashbang always (including sourced files)
- Support `--help` and `--version`; list dependencies
- Check deps before run; on TTY offer preferred installer when known
- Fail gracefully; solid errors/exit codes
- Colors: `ansi-colors.md`; print stack: prefer `pansi` when needed; logging:
  prefer `plog` (query, never raw `tail` at TRACE) — see those catalog files
- Comments: `comments.md`
- Prefer single-file ~500–1000 lines; larger → multi-file project
- Almost never emoji in code (except test ✓/X)

## Missing dependencies (FIRM)

Before first use of a required tool: `command -v` / `shutil.which`. Message names the tool + preferred install. Exit **127** for missing binary.

Install path preference: (1) shellrc `install-<tool>` / `user-install-<tool>`, (2) distro package, (3) upstream. Do not invent names.

| Mode | Behavior |
| --- | --- |
| Interactive TTY | Ask to install (default yes for user-scoped; no for sudo/system) |
| Non-interactive / CI | Never auto-install; print command; exit 127 |

## User dests and root (FIRM)

Root must not own anything under `$HOME` — full rule in `security.md`.

When an installer runs as root or via `sudo`:

- Write user files (`~/.local/…`, `~/.config/…`) as the home owner
- After a write, dest owner must be that user, not root
- Repair leftover root-owned dests for **this tool’s filenames only**
- Never `chown -R` a shared XDG tree

`sudo` is for system paths (`/usr`, apt, PPA). `$HOME` stays the user’s.

## Interactive vs script mode

Detect TTY on stdin+stdout.

| Mode | Destructive ops |
| --- | --- |
| Interactive | Confirm (prefer exact `yes` for high risk) |
| Script/CI | **Refuse** unless `--force` (or equally explicit flag) |

Never assume “yes” non-interactively for delete/overwrite/wipe/foreign-host apply.

## User-facing launches from Grok (FIRM)

Grok agent tools often run with a **monochrome sandbox**: `NO_COLOR=1`,
`FORCE_COLOR=0`, `TERM=dumb`, plus tool-specific `*_NO_COLOR` / `CLICOLOR=0`.
That is correct for machine-parsed tool output. It is **wrong** for anything the
human will look at in a real terminal or desktop window.

**Always** strip the agent sandbox when launching user-visible work, for example:

- Desk/layout: `forge layout dev`, `forge layout <name>`, `forge launch …`
- Terminals/editors/browsers opened for the user
- Interactive CLIs the user will read (colored status, TUI apps)

### Recipe

Prefer the shellrc helper (on PATH after `shellrc` install):

```bash
user-env forge layout dev
user-env ghostty -e zsh -lic 'cd ~/dev/me/forge && exec zsh'
user-env -- npm run dev   # -- ends flags
```

If `user-env` is missing, equivalent minimal reset:

```bash
env -u NO_COLOR -u PIP_NO_COLOR -u NPM_CONFIG_COLOR \
  -u CARGO_TERM_COLOR -u CLICOLOR -u CLICOLOR_FORCE \
  TERM="${TERM/#dumb/xterm-256color}" \
  FORCE_COLOR=1 CLICOLOR_FORCE=1 \
  forge layout dev
```

| Keep | Drop / override |
| --- | --- |
| `PATH`, `DISPLAY`, `XDG_*`, credentials, project env | `NO_COLOR`, `FORCE_COLOR=0`, `CLICOLOR=0`, `TERM=dumb` |
| `GROK_LEADER_SOCKET` (harmless for most apps) | Agent-only monochrome `*_NO_COLOR` / `*_COLOR=never` |

Do **not** wrap pure agent/CI tool steps in `user-env` — keep monochrome there so
logs stay parseable. Leader-mode detection: `testing.md`.

After **headless / detached** Grok work (or tests that closed the launch TTY):
open a terminal and **reattach** the durable head for the human
(`user-env grok` / `grok --attach` / `grok -r …`) — full rule in `testing.md`.

## Args

- Python: `argparse`
- zsh: prefer `--key=value`; `zparseopts` when needed
- Destructive ops pair with `--force` for non-interactive

## Shell

`set -euo pipefail` · `local` · quote vars · `[[ ]]` · `trap` cleanup · `emulate -L zsh` when sourced · `exec` final command in env wrappers.

## Language choice

| Prefer | When |
| --- | --- |
| zsh | Wrappers, small installers |
| bash/POSIX | Must run where only sh exists |
| Python 3 | Complex logic/data |
| Lua | Minimal footprint when appropriate |
| JS | When project is already JS |
