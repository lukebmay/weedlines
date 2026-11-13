---
title: Scripting
order: 40
---

# Scripting

When to use: Writing or changing shell/Python scripts, installers, CLI tools, bin entries, or launching user-visible apps from a Grok agent.

Assume **Linux** (Ubuntu LTS unless stated). Prefer portable choices when cheap.

Language style: `agents/languages/<lang>.md` when relevant. In-repo formatter/LSP wins.

## All scripts

- Hashbang always (including sourced files)
- Support `--help` and `--version`; list dependencies
- Check deps before run; on TTY offer preferred installer when known
- Fail gracefully; solid errors/exit codes
- Colors: `ansi-colors.md`. `NO_COLOR` and `TERM=dumb` stay on for output the agent parses, and come off only for a program a person will look at.
- Comments: `comments.md`
- Prefer single-file ~500–1000 lines; larger → multi-file project.
  Not the rule for all source; that is `Source files` in `agents/handbook.md`
- Almost never emoji in code (except test ✓/X)

## Missing dependencies (FIRM)

Before first use of a required tool: `command -v` / `shutil.which`. Message names the tool + preferred install. Exit **127** for missing binary.

Name the tool and a real install command. Do not invent names.

| Mode | Behavior |
| --- | --- |
| Interactive TTY | Ask to install (default yes for user-scoped; no for sudo/system) |
| Non-interactive / CI | Do not auto-install; print the command; exit 127 |

This table is how the script behaves when a tool is missing. It is not a
ban on an install the current message asks the agent to run.

## User dests and root (FIRM)

Root must not own anything under `$HOME` — full rule in `security.md`.

When an installer runs as root or via `sudo`:

- Write user files (`~/.local/…`, `~/.config/…`) as the home owner
- After a write, dest owner must be that user, not root
- Repair leftover root-owned dests for **this tool’s filenames only**
- Never `chown -R` a shared XDG tree

`sudo` is for system paths (`/usr`, apt, PPA). `$HOME` stays the user’s.

## XDG directory variables (FIRM)

A user install uses one variable per home the program stores.
A missing variable means the default. A set variable wins.

- `<APP>_CONFIG_DIR` defaults to `$XDG_CONFIG_HOME/<app>`, or
  `~/.config/<app>` when `XDG_CONFIG_HOME` is unset.
- `<APP>_DATA_DIR` defaults to `$XDG_DATA_HOME/<app>`, or
  `~/.local/share/<app>` when `XDG_DATA_HOME` is unset.
- `<APP>_STATE_DIR` defaults to `$XDG_STATE_HOME/<app>`, or
  `~/.local/state/<app>` when `XDG_STATE_HOME` is unset.
  Logs on a user install stay in the state directory.
  There is no separate log variable. XDG has no log home.
- `<APP>_CACHE_DIR` defaults to `$XDG_CACHE_HOME/<app>`, or
  `~/.cache/<app>` when `XDG_CACHE_HOME` is unset.
- `<APP>_RUNTIME_DIR` defaults to `$XDG_RUNTIME_DIR/<app>`.
  No home fallback. If both `<APP>_RUNTIME_DIR` and
  `XDG_RUNTIME_DIR` are unset, fail. Do not use `/tmp`.

Records that differ per machine go in `$<APP>_*_DIR/hosts/<hostname>/`.
`<hostname>` is the kernel hostname. Records reused on every host
go directly in `$<APP>_*_DIR`. Pick one. Do not read both.
Runtime has no `hosts/` directory, because `XDG_RUNTIME_DIR` is
already local to the machine.

A system install does not write `$HOME`. Config uses
`XDG_CONFIG_DIRS` (default `/etc/xdg`). Data uses `XDG_DATA_DIRS`
(default `/usr/local/share:/usr/share`). XDG does not name system
state, cache, or runtime. State is `/var/lib/<app>`, cache is
`/var/cache/<app>`, logs are `/var/log/<app>`, and runtime is
`/run/<app>`. The same variables override those paths.

Root still does not own files under `$HOME`. The full rule is
User dests and root, above.

## Elevate only the privileged step (FIRM)

The user runs the command in their normal shell. They do not prefix it with `sudo`, and they do not keep a separate root shell for it.

When a step needs root, the script elevates that step. The rest stays the invoking user, so files under `$HOME` are not created as root.

- Interactive: `sudo` may prompt. Say which step needs it.
- Non-interactive: do not hang on a password. If the step cannot elevate without a prompt, print the command and exit.
- Do not re-exec the whole script as root.

Whether the agent may elevate is `security.md`. This section is how the script is written, not permission to elevate.

## Interactive vs script mode

Detect TTY on stdin+stdout.

| Mode | Destructive ops |
| --- | --- |
| Interactive | Confirm (prefer exact `yes` for high risk) |
| Script/CI | **Refuse** unless `--force` (or equally explicit flag) |

Do not assume “yes” when the script is non-interactive, for a delete,
overwrite, wipe, or foreign-host apply. This is the script. A delete,
overwrite, or wipe the current message already names does not need a
second ask. Foreign-host apply still follows `security.md`.

## Color for people and for parsers

`NO_COLOR` and `TERM=dumb` stay on for output the agent parses, and come off only for a program a person will look at.

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
