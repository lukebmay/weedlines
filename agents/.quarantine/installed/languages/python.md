---
title: Python
read_when: Writing or reviewing Python
order: 200
---

# Python

**Precedence:** `pyproject.toml`, `ruff`/`yapf`/`black`, `pyrightconfig.json`/`mypy`, `.editorconfig` override this file.

shellrc inspiration: line length **100**; ruff F/E/W; yapf pep8 + `split_before_logical_operator`; mypy strict where enabled; pyright 3.12.

## When

Complex logic, rich options, data processing, anything heavier than a shell one-liner.

## shellrc scripts layout

| Size | Layout |
| --- | --- |
| Small tool | Single file `scripts/…/name.py` → `bin/name` |
| Multi-module app | Package under `scripts/…/<name>/` with `__init__.py` + `__main__.py` |

Package trees are **not** flattened into `bin/`. Only the package with `__main__.py` gets a launcher at `bin/<name>`. Library modules may keep shebangs and `if __name__ == "__main__":` smoke tests — that does **not** install them.

Full installer rules (and other languages): `agents/scripts-build.md`. Example: `scripts/devices/displays/gdisplays/` → `bin/gdisplays`.

## Style

- Hashbang: `#!/usr/bin/env python3` (no hard-coded venv paths). Tools that must work under `sudo` may use `#!/usr/bin/python3` when documented.
- CLI apps: package `__main__.py` (or single-file `if __name__ == "__main__":`)
- Args: `argparse`
- Prefer stdlib; document third-party deps
- Simple data: `dataclass` over heavy class hierarchies
- Clarity over paradigm; classes when they reduce complexity
- Type hints encouraged on public APIs; match project strictness
- Snake_case modules/functions; CapWords classes
- Virtualenv: document activation; do not assume a fixed path
- Relative imports inside packages (`from .foo import bar`)

## Tools

- Format: project’s `yapf` / `ruff format` / `black` (use whatever the repo already runs)
- Lint: `ruff` / `flake8` as configured
- Types: `pyright` / `mypy` as configured
