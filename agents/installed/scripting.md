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

## XDG install (FIRM)

This is how a user-facing application is installed into the
XDG homes. It is not how every repository is installed.

A repository whose files are one person's machine stays a
checkout. Shell startup, private aliases, and a private
config tree are that kind of repository. An extension
installs by the host's own mechanism. A later split may
publish a shared program and keep a private user directory.
That split is a different plan. This section does not do it.

The release install is the default. `./install` with no
flag, `curl -fsSL <public-url>/install | sh`, and
`<app> update` all do this. `<app> update <ref>` does this
from `<ref>`. `<ref>` is a commit or a branch. It prints
a warning that `<ref>` is not the release.

The release ref is the one the project's guide names. When
the guide names none, use a branch named `release` when
that ref exists on the public remote. Otherwise use
`master` when it exists, otherwise `main`. When none of
those exist, fail and name the refs that were tried.

The public URL is `https`, recorded when the command is
installed. Download that ref into `$XDG_CACHE_HOME/<app>/src`,
or `~/.cache/<app>/src` when `XDG_CACHE_HOME` is unset.
Copy the snapshot into `$XDG_DATA_HOME/<app>`, or
`~/.local/share/<app>`. The copy contains no `.git`.
`~/.local/bin/<app>` points at the copy's executable. The
cache directory is only the download. No installed command
runs from it. Deleting the cache, or deleting any checkout,
leaves the installed command working.

A release install does not record a developer checkout. It
does not fetch, pull, or write one. `./install` from inside
a checkout ignores that checkout and prints that local edits
were not installed. The download does not require git. Git
is required only for a dev install. The script refuses to
run as root and writes only the user prefix. `--dev` fails
when the script is piped, because a pipe has no checkout.

`<app> update` with no ref installs the release ref again.
`<app> update <ref>` installs that commit or branch, prints
the warning, and does not record `<ref>`. The next
`<app> update` with no ref returns to the release ref.
Either result is a release install.

`./install --dev` makes `<app> install` a command.
`<app> install --dev` keeps that command. `<app> install`
with no flag is a release install, and so is `./install`
with no flag. After either, the installed command does
not accept `<app> install` until a later `./install --dev`.

A dev install is `./install --dev` from a git checkout, and
later `<app> install --dev`. `./install --dev` records that
checkout. The path is installer state, under
`$<APP>_STATE_DIR/hosts/<hostname>/`. Copy that directory
as it sits, including uncommitted files, into the data home.
Do not fetch. Then install the tools the project names in
its guide. An empty tool list still leaves a dev install.
Editing the checkout does not change the running command
until the next dev install. The last checkout recorded
wins.

A missing recorded path fails and names the path.
Do not search the disk. Do not fall back to a release.
`--dev` from a directory that is not a checkout fails.

The installed command records the config, data, and state
roots from the install. A process that did not set the
variable uses those recorded roots. A variable already set
in the environment wins. The record is installer state.
It is not a settings key the person edits. A shell rc is
not required for the command to find those roots.

Uninstall removes `~/.local/bin/<app>` and the data-home
copy. It leaves the developer checkout, the config home,
and the state home.

Runtime commands do not call git. The version is a file in
the snapshot. The running install is a copy in the XDG
homes. It is not a link into a git worktree.

Each project names its public install URL and, when it
wants one, its release ref. Those facts live in that
project's guide, not in this file.

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
