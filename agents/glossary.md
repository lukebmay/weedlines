# Glossary

**Owner:** agent. Agents read and write this file. Keep it human-readable.

Words used across the handbook. Product-specific terms belong in the
project section below. Process terms are shared across repos that use
this catalog.

If two handbook sentences still make sense after swapping two of these
words, rewrite them.

Leftover identifiers still in code or old docs are tracked in
[`conflicts.md`](./conflicts.md). This file stays the law for the
target words.

## Handbook

| Word | Meaning |
| --- | --- |
| **handbook** | The `agents/` directory: policies and procedures for agents operating on this codebase. In prose, say handbook, not “the agents folder.” |
| **stone** | Product or architecture law. Lives only in human-owned handbook files (`architecture.md`, `acceptance.md`, and any project-declared stricter file). Chat, plan Session, and `priority.md` quotes are not stone. |
| **leftover** | An old name, path, or behavior still in code or docs that the handbook no longer teaches. Track it in `conflicts.md`. Do not mint more of it. |
| **one home per fact** | A rule lives in exactly one file. Other files link; they do not restate. |
| **catalog** | Portable guideline fragments under `agents/installed/`, refreshed by the `agents` CLI. Handbook files win on conflict. |
| **extension** | Project file at `agents/<same-path-as-installed>` (or `*.extend.md`) that amends a catalog file. |
| **override** | Project file `agents/<stem>.override.md` that replaces an installed catalog file for that id. Rare. |
| **human-owned** | File agents may propose edits to; apply only with explicit permission in the current message. |
| **agent-owned** | File agents update as ordinary work (`glossary.md`, `priority.md`, `conflicts.md`, plan Session). |
| **explicit** | Permission word required in the **current** user message for remote SSH or root execution. See catalog `always.md`. |

## Work

| Word | Meaning |
| --- | --- |
| **plan** | The unit of work. One file under `agents/plans/`. Holds goal, acceptance, approach, Human waits, and Session notes. |
| **slice** | A bite-sized step inside a plan. Not a second work type. |
| **Session** | The plan section for the next agent on that plan. Overwrite; do not pile. Not stone. |
| **Human** | The plan section that only a person can complete (checkboxes). A human wait is plan state, labeled in `priority.md`. |
| **Approach** | How this plan is built. Do not restate global architecture here. |
| **Goal** | What this plan makes true. |
| **Acceptance** | Checks that must hold for the plan (local) or for any work (product file `acceptance.md`). |
| **priority** | `agents/priority.md`: ordered list of plans. Agent-owned. |
| **idea** | Parked thought in `agents/ideas/`. Not a plan until it has a goal and acceptance. |
| **wrap-up** | End of a successful slice: residue, notes, tests, commit/push per `git.md`. |
| **residue** | Temp paths, debug prints, failed-attempt code, fake fixtures, live-env leftovers the agent added. Remove before finishing. |

## Product files

| Word | Meaning |
| --- | --- |
| **architecture** | `agents/architecture.md`: the **target** system, not a snapshot of today's tree. Human-owned. Can be wrong — stop and meet. |
| **acceptance** | `agents/acceptance.md`: when work is complete. Human-owned. |
| **conflicts** | `agents/conflicts.md`: leftover names and contradictions. Agent-owned. Not a second architecture. |
| **project** | `agents/project.md`: what the product is. Human-owned. |
| **dest** | Destination path a tool writes. Repair only this tool’s dests; never `chown -R` a shared tree. |
| **live data** | State whose wrong change costs real time, money, or irreplaceable files. Backup or `--dry-run` first. |
| **dry-run** | Print every destructive step and exit with zero writes. |
| **daily driver** | The machine/login the operator uses for real work. Do not treat it as a disposable test host. |

## Rule labels

| Word | Meaning |
| --- | --- |
| **FIRM** | Must follow. Escalate or stop if you cannot. |
| **GUIDELINE** | Default. Override only with clear reason. |
| **MAY** | Optional. |

## Do not confuse

| Do not write | Write |
| --- | --- |
| `design.md` / design changelog as living law | **architecture.md** + **conflicts.md** |
| `HANDOFF.md` as the start-here file | Plan **Session** + **priority.md** |
| `PRIORITY.md` (ALL-CAPS) as the queue | **priority.md** |
| A separate `blockers/` item as the unit of work | Plan **Human** section, labeled in **priority.md** |
| Chat “don’t do X” as architecture | A lock **with why** in architecture, or a slice fence on the plan |

## Project words

Add product-specific terms here. Keep process terms above in sync with
the catalog handbook glossary.
