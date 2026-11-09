---
title: ANSI colors
order: 80
---

# ANSI Colors

When to use: Adding terminal colors, formatting CLI output, or launching user-visible CLIs from a Grok agent.

Portable **color contract** for CLIs.
Implement via the project's color helper when it has one. Do not invent a third policy per script.

This fragment is **library-agnostic**: it does not require pansi/plog. It only
defines *whether* and *which roles* to color.

## Modes

| Mode | Meaning |
| --- | --- |
| **`auto`** (default) | Color only when the **output stream** is a TTY **or** a force-env applies |
| **`always`** | Always emit ANSI (`less -R`, a log a person will read) |
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

Optional tool-specific env is an alias for step 4 / mode override: values `always|never|auto` only. Same decision order.

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

## Rules

- Reset after every sequence (`\033[0m` / equivalent)
- No external ANSI libs unless the project already standardized on one
- This file decides whether to color. Printing and logging stay with the project's own tools.
- Prefix portable helper ids with `ansi_` when not in a dedicated module

## Personal preference vs machines

| Context | Policy |
| --- | --- |
| **Interactive human** | Default `auto` is enough on a TTY. Optional interactive-only `CLICOLOR_FORCE=1` / `FORCE_COLOR=1` if you always want color (including some pipes) |
| **Pipes / grep / scripts** | `auto` without force → plain. Forced color **can** break `grep` / parsers |
| **Output the agent parses** | `NO_COLOR` and `TERM=dumb` stay on |
| **A program a person will look at** | Those come off |

**Do not** hardcode always-on inside CLIs. Put personal force in **interactive**
shell config only — never in `zshenv` (scripts inherit that).

`ls --color=auto | grep` is safe. `ls --color=always | grep` or
`CLICOLOR_FORCE=1` into a pipe is not.

## Agent output

`NO_COLOR` and `TERM=dumb` stay on for output the agent parses, and come off only for a program a person will look at. The decision order above still applies.

New scripts call the project's color helper. Do not open-code `[[ -t 1 ]]` alone.
