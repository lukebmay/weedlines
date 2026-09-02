# Project notes

**This is the only file you must fill out after `agents init`.**

Project-specific conventions and stack. Safe for humans to edit.
Managed portable fragments live under `agents/installed/` (via `agents`
install/update) — do not put portable rules here.

## Ownership (quick)

| Path | Who |
| --- | --- |
| **`agents/project.md`** (this file) | **You** — conventions, stack, env, offline rules, … |
| **CAPS files** (`HANDOFF.md`, `PRIORITY.md`, `CHANGELOG.md`, …) | **Agents** manage these. You *may* edit by hand; that is not the intended workflow. |
| **`agents/design.md`** | Guiding-light design (high-level picture, key inner workings, important tech choices + reasoning). **Not** a novel of every decision. Created after the first design meeting (by agents or you). Optional until then. |
| **`agents/plans/`** | Work plans — agents + you via PRIORITY |

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
