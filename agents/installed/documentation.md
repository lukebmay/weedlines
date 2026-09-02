---
title: Documentation
read_when: Writing design docs, design CHANGELOG, user docs, human-facing checklists/blockers, or choosing where “why” lives
order: 60
---

# Documentation

## Audience (FIRM)

Match the reader. **Human-facing** files (`agents/blockers/`, `docs/user/*`,
and any checklist a human must complete) are written for how humans process
text: top→bottom, acting and answering **inline as they read**.

| Rule | Detail |
| --- | --- |
| Process-as-you-read | Order steps so the human can do each item and respond beside it while reading |
| Checkboxes over protocols | Prefer `- [ ]` / `- [x]` the human ticks; do not end with a post-read “report PASS/FAIL per item” ritual |
| No agent noise | Omit agent prep dumps, hunt recipes, internal IDs, and restated “done when” lists the human cannot use |
| One reason line | “Why human-only” (or similar) is one short sentence when possible |
| Actions only | Warnings and agent-only procedure belong in HANDOFF / plan notes — not the human checklist |

**Agent-facing** files (`HANDOFF.md`, `PRIORITY.md`, plan session notes) stay
functionally detailed for the next agent. That density is wrong on a human
checklist.

## Where “why” lives

| Doc | Role |
| --- | --- |
| `agents/design.md` | **Guiding light** — high-level picture, key inner workings, important tech choices + reasoning. Not every decision in the project. |
| DESIGN `## Overview` / `## AGENTS.md View` | Small compass; `agents build` **parses and inlines** into `AGENTS.md` |
| `agents/design/CHANGELOG.md` | Thin dated locks / supersessions (was `docs/DECISIONS.md`; **agent-managed**) |
| `agents/design/*` | Optional topic detail |
| `docs/user/*` | Human/user-facing docs after meetings; examples; benefits |
| `agents/HANDOFF.md` / plan notes | Cold-continue (**agent-managed** CAPS) |
| `agents/plans/` · `agents/PRIORITY.md` | Execution |
| `agents/project.md` | User conventions / stack |
| Source comments | Minimal *why* only — `comments.md` |

Put durable guiding *why* in `agents/design.md`; history in CHANGELOG. Keep
volatile checklists out of design.md.

## `agents/design.md` (guiding light)

- High-level picture of how things should work
- Important details of key inner workings
- Key tech choices and reasoning
- **Not** a comprehensive document of all design choices in every aspect
- Keep Overview / AGENTS.md View **small** (token budget)
- Create after the first design meeting (agents or user) — optional on fresh init
- When design changes **user-visible** behavior: update `docs/user/*` in the
  same effort. Do **not** auto-generate user prose from design bullets.

## CAPS files (agent-managed)

`HANDOFF.md`, `PRIORITY.md`, `CHANGELOG.md`, generated `AGENTS.md`, and other
**ALL-CAPS** names under `agents/` are **agent-managed**. Manual edits are
allowed but not the intended workflow.

## `agents/design/CHANGELOG.md` shape

Thin history — not a rival design novel:

| Date | ID | Topic | Status | Lock / supersession | Why |
| --- | --- | --- | --- | --- | --- |
| YYYY-MM-DD | D001 | deploy | active | … | one line |

Status: active | superseded | rejected.

When shipping a non-obvious choice: update `agents/design.md` if the guiding
narrative changed; add a CHANGELOG row for the lock/supersession.

### Precedence (FIRM)

**Newest design meeting / CHANGELOG row for a topic wins.** Mark older rows
superseded; do not silently edit history. Accepted meeting locks and plan
“Status: Accepted” sections outrank older plan draft prose on the same
question. Full rule: catalog **`general.md`** § Design.

## Hygiene

- No secrets or real credentials
- Prefer archive of superseded plans over delete
- Fix stale design.md / CHANGELOG / user-doc claims when you touch the area
