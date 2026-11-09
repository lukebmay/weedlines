---
title: Python
order: 200
---

# Python

When to use: Writing or reviewing Python.

**Precedence:** `pyproject.toml`, `ruff`/`yapf`/`black`, `pyrightconfig.json`/`mypy`, `.editorconfig` override this file.

## When

Complex logic, rich options, data processing, anything heavier than a shell one-liner.

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
