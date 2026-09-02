---
title: ANSI colors
read_when: Adding terminal colors, formatting CLI output, or launching user-visible CLIs from a Grok agent
order: 80
---

# ANSI Colors

Portable **color contract** for this stack (shellrc, forge, and other CLIs).
Implement via the shared **`ansi_color`** helpers when available (see
**Shared library**). Do not invent a third policy per script.

This fragment is **library-agnostic**: it does not require pansi/plog. It only
defines *whether* and *which roles* to color.

## Modes

| Mode | Meaning |
| --- | --- |
| **`auto`** (default) | Color only when the **output stream** is a TTY **or** a force-env applies |
| **`always`** | Always emit ANSI (pdsh, job log attach, `less -R`) |
| **`never`** | Never emit ANSI |

CLI flag (every user-facing tool that colors):

```text
--color=auto|always|never
```

Bare `--color` (no value) ⇒ **`always`** when a tool accepts it.

## Decision order (FIRM)

Identical in every language. First match wins:

```text
1. --color=never          → never
2. --color=always         → always
3. NO_COLOR set (any non-empty value) → never
4. FORCE_COLOR set and non-empty and not 0/false/no/off
   OR CLICOLOR_FORCE set and non-empty and not 0/false/no/off
   OR COLOR=always / TOOL_COLOR=always / <TOOL>_COLOR=always
                          → always
5. mode auto + stream.isatty() → always (color on)
6. else                   → never
```

Notes:

- **`--color` beats env** for that invocation.
- **`NO_COLOR` beats force envs** (agents/CI stay plain even if the profile exports `CLICOLOR_FORCE`).
- Check **the stream you write to** (stdout vs stderr), not always fd 1.
- Re-evaluate at **print time** (or re-init after parsing flags). Do not freeze
  color on library source if flags can change mode later.
- **Structured / machine output** (`--json`, porcelain, parseable status) is
  always plain — never gate only on color mode.

Optional tool-specific env (`FORGE_COLOR`, `GDISPLAYS_COLOR`, …) is an alias for
step 4 / mode override: values `always|never|auto` only. Same decision order.

## Roles

| Color | Use |
| --- | --- |
| **Cyan** | Files, dirs, URLs, identifiers; main table values |
| **Blue** | Runnable commands; standout numbers/versions |
| **Magenta** | Headings, labels, section names |
| **Green** | Success |
| **Red** | Errors |
| **Yellow** | Warnings (paths/ids in yellow warnings: use **blue**, not cyan) |
| **Default** | Keys, punctuation, body |

Tables: default keys, colored values. Times: default parens, blue number.
Green `✓` only for step ticks — not overall success lines.

## Choosing a print / log stack (GUIDELINE)

**ansi-colors** = enablement + role palette. Pair with a printer/logger:

| Need | Prefer | Catalog |
| --- | --- | --- |
| Styled print / string build | **pansi** (`p` / `pstr`) when the project has no color printer, or the existing one is ad-hoc / inconsistent | `pansi` |
| Levels, files, sessions, searchable logs | **plog** (+ dual-tape / `plog-query`) when there is no real logger, or logging is `print`/`console.log` soup | `plog` |
| Project already standardized | **Keep that system** — do not dual-stack | — |

Install `pansi` / `plog` into a repo with `agents install` only when that repo
uses (or is adopting) them. Do **not** force them into unrelated projects.

Hunt logs with **query** (`plog-query` / `app log --grep …`), never raw `tail`
at TRACE — see **`plog`**.

## Rules

- Reset after every sequence (`\033[0m` / equivalent)
- No external ANSI libs unless the project already standardized on one
- Prefer **pansi** / project `p`·`pstr` for *printing* when adopted; prefer
  **`ansi_color`** for *whether* to color
- Prefix portable helper ids with `ansi_` when not in a dedicated module

## Personal preference vs machines

| Context | Policy |
| --- | --- |
| **Interactive human** | Default `auto` is enough on a TTY. Optional interactive-only `CLICOLOR_FORCE=1` / `FORCE_COLOR=1` if you always want color (including some pipes) |
| **Pipes / grep / scripts** | `auto` without force → plain. Forced color **can** break `grep` / parsers |
| **AI / agent tools** | `NO_COLOR=1` (and often `TERM=dumb`) — correct |
| **User-visible launches from agents** | **`user-env`** (or scripting.md recipe) strips monochrome sandbox |

**Do not** hardcode always-on inside CLIs. Put personal force in **interactive**
shell config only — never in `zshenv` (scripts inherit that).

`ls --color=auto | grep` is safe. `ls --color=always | grep` or
`CLICOLOR_FORCE=1` into a pipe is not.

## pdsh / remote fan-out

Remote commands under `pdsh` almost never have a TTY (stdout is a pipe).
Strict `auto` + `isatty` alone → monochrome. That is expected.

**Human-facing pdsh** (reasonable default for wrappers/drivers):

```text
if driver stdout is a TTY
   and NO_COLOR is unset
   and user did not pass --color=never
→ inject FORCE_COLOR=1 and CLICOLOR_FORCE=1 on the remote command
  (or pass --color=always to tools that support it)
else
→ leave auto / plain
```

Detect **local driver TTY** (`[[ -t 1 ]]`), not “interactive shell” alone
(so `pdsh … | grep` and redirects stay plain). SSH does not forward arbitrary
env; **prefix the remote command** (or use an explicit wrapper).

Keep a separate **collect/parse** path: `NO_COLOR=1` and/or `--json` / never.

See also `pdsh.md` for fan-out safety rules.

## Durable job runners (e.g. forge jobs)

Workers often log to files (no TTY). If the **attaching** parent will display
on a TTY and wants color, set `FORGE_COLOR=always` (or equivalent) **in the
worker env** so ANSI is written into logs that attach streams to the terminal.
Still honor `NO_COLOR` / `--color=never` on the parent.

Do **not** leak job-worker env markers (`FORGE_JOB_WORKER`, job id/dir,
`FORGE_JOB=0` nesting disable) into desktop terminals spawned by layout/launch.

## Agent tools vs user-facing (FIRM)

Grok agent turns often set `NO_COLOR=1` / `TERM=dumb`. That is for **tool logs**,
not for apps the human will use. When launching user-visible CLIs, layouts, or
terminals from an agent, wrap with **`user-env`** (or the env recipe in
`scripting.md`) so colors and a normal `TERM` are restored. Do not leave
`NO_COLOR=1` on `forge layout …`, `ghostty`, etc.

## Shared library

Canonical implementations live in shellrc (versioned; same contract):

| Lang | Path |
| --- | --- |
| Python | `util/python/ansi_color.py` |
| Zsh | `util/zsh/script-utils/ansi_color.zsh` |
| JS | `util/js/ansi_color.js` |
| Lua | `util/lua/ansi_color.lua` |

Each file exports:

| Symbol | Role |
| --- | --- |
| **`ANSI_COLOR_VERSION`** | Semver string of this contract implementation (e.g. `1.0.0`) |
| **`resolve_color_mode(...)`** | Returns `always` \| `never` \| `auto` after flag/env |
| **`color_enabled(...)`** | Bool for a given stream/fd after full decision order |

**Drift detection:** every vendored copy (e.g. forge `scripts/forge/ansi_color.py`)
must set the **same** `ANSI_COLOR_VERSION`. If versions differ, treat as a bug —
update the lagging copy from shellrc.

New scripts: call the helper; do not open-code `[[ -t 1 ]]` alone.
Migration of existing scripts: see shellrc task `ansi-color-contract-migrate`
(when present under `agents/tasks/`).
