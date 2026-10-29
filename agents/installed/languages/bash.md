---
title: Bash
read_when: Writing or reviewing Bash scripts
order: 200
---

# bash

**Precedence:** in-repo `.editorconfig`, `shfmt`, shellcheck, and project scripts override this file.

## When

Use when the script must run on systems without zsh, or when targeting pure bash/POSIX. Prefer **zsh** inside shellrc.

## Style

- Hashbang: `#!/usr/bin/env bash` (or `#!/bin/sh` only for strict POSIX)
- Indent 2 spaces; Unix newlines
- `set -euo pipefail` (bash 4+); note `pipefail` is bash/ksh, not plain POSIX sh
- Quote `"$var"` / `"$(cmd)"`; prefer `[[ ]]` in bash
- `local` in functions; `trap` for cleanup
- Prefer bash builtins over `sed`/`awk` forks when simple
- Args: getopts for simple flags; hand-parse `--key=value` if needed
- `--help` / `--version`; list and check dependencies

## Tools

- Format: `shfmt -i 2`
- Lint: `shellcheck -s bash`
