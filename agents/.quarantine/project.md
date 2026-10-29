# Project

**Owner:** human. Agents may propose edits; apply only with explicit permission.

## What this is

Weedlines is an Inkscape extension and shared solvers for weed cuts on
vinyl. How it is built: [`architecture.md`](./architecture.md).

## Stack

| Piece | Detail |
| --- | --- |
| Language | Python ≥ 3.9 |
| Layout | `src/weedlib/` (solvers) · `src/weedlines/` (CLI) · `extensions/inkscape/` |
| Packaging | setuptools editable (`pip install -e '.[island-hop,dev]'`) |
| UI | Inkscape extension dialog (Qt binding: PyQt5/6 or PySide6) |
| Optional | `pyclipper` for `island-hop` |
| Tests | pytest (`tests/`) |
| GitHub | `lukebmay/weedlines` |

## Commands

```bash
./install                  # editable pip (if needed) + Inkscape extension symlink
weedlines install          # symlink into ~/.config/inkscape/extensions
weedlines update           # git pull if clean, then install
pytest                     # unit tests
```

## Logging

| Env | Effect |
| --- | --- |
| unset / `WEEDLINES_LOG=0` | Quiet (default) |
| `WEEDLINES_LOG=1` | Decisions, phases, rejects, audits |
| `WEEDLINES_LOG=2` / `trace` | Also every `emit.accept` |

Legacy alias: `INKCUT_WEED_DEBUG`.

## Conventions

- Default algorithm mode is `frame`. Do **not** treat `island-hop` as
  production-default until picture QA is accepted.
- Prefer `weedlib` APIs over copying solver logic into the extension.
- Keep this repo standalone until algorithms are solid; optional Inkcut
  re-integration later.
