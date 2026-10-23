---
title: Documentation
read_when: Writing architecture, user docs, human-facing checklists, or choosing where “why” lives
order: 60
version: 4.5.0
---

# Documentation

## Audience (FIRM)

Match the reader. **Human-facing** files (`docs/user/*`, plan **Human**
sections, and any checklist a human must complete) are written for how
humans process text: top→bottom, acting and answering **inline as they
read**.

| Rule | Detail |
| --- | --- |
| Process-as-you-read | Order steps so the human can do each item and respond beside it while reading |
| Checkboxes over protocols | Prefer `- [ ]` / `- [x]` the human ticks; do not end with a post-read “report PASS/FAIL per item” ritual |
| No agent noise | Omit agent prep dumps, hunt recipes, internal IDs, and restated “done when” lists the human cannot use |
| One reason line | “Why human-only” (or similar) is one short sentence when possible |
| Actions only | Warnings and agent-only procedure belong in the handoff on the plan — not the human checklist |

**Agent-facing** files (`priority.md`, the handoff on the plan) stay
functionally detailed for the next agent. That density is wrong on a
human checklist.

## Where writing lives

| Kind | Place |
| --- | --- |
| Product README (install and usage) | Repo-root `README.md`. **Human-owned.** Agents read it; write only with explicit permission in the current message. Anything beyond install and basic usage belongs in `docs/`. |
| What the product is | `agents/project.md` |
| How it is built and how it runs (the guide) | `agents/architecture.md`. What that guide is, and what it refuses to become, is catalog `general.md` What is stone |
| Who the human is and how to collaborate | `agents/human.md`. Not product law |
| What words mean | `agents/glossary.md` |
| Open rule conflicts and leftovers | `agents/conflicts.md`. **Active** and **Leftovers**, as catalog `general.md` Conflicts |
| Retired conflict decisions | `agents/conflicts-resolved.md`. Not rules. The order is catalog `general.md` Conflicts |
| When work is complete | `agents/acceptance.md` |
| This piece of work | a file under `agents/plans/` |
| How we test | `agents/testing.md` (project) / catalog `testing.md` |
| User-facing help | `docs/user/` |
| Named code APIs | `docs/dev/` when the project has one |

Agents do not take product rules from `docs/`. Target behavior is
`architecture.md` and `acceptance.md`. `docs/user/` is human-facing.
`docs/dev/` is a code map and API catalog that can lag; if it disagrees
with architecture, architecture wins.

Do not add a second architecture, glossary, or acceptance in a plan,
priority note, or conflict row. Conflicts, stone, and what a lock
contains: catalog `general.md`. User-visible behavior updates
`docs/user/` in the same effort.

## Architecture writing (FIRM)

What *is* written must be **crystal clear**. A later agent or human must
act correctly **without guessing**. Unclear architecture is a bug: people
will treat a vague sentence as a permanent veto and ship around it.
The file is a guide of what has worked and what has failed. It is
not a history, and an old sentence is not kept because it is old.

| Rule | Detail |
| --- | --- |
| **No room to interpret** | If two readers can honestly disagree on who/what/when, rewrite. If a sentence still works after swapping two domain words, it is too vague |
| **Name the actor** | Say **who** does the thing. Do not say “write”, “observe”, “desired”, “recompute” unless the sentence also says **which layer and which value** |
| **Context in the architecture** | A sentence names who does what, and what it does not cover. One sentence of why when the choice is easy to undo the wrong way. Do not record rejected alternatives, the date, or the incident |
| **Plans inherit the clarity bar** | A plan states the goal and the approach. It does not copy a rejected-alternatives essay. The handoff is the summary on that plan. The rule is catalog `general.md`. It is overwritten, and it is not a second architecture |

### Cross-lock update (FIRM)

When you change a **core element** that another lock, plan, or glossary
uses (a word, invariant, identity, …):

1. Find every architecture section, plan, and glossary entry that
   depends on it.
1. Update, supersede, or translate those **in the same effort**.
1. If you cannot: **stop and ask**. Do not ship a lock that silently
   contradicts another.

## Task ids and links

First use of a short id includes the human name. Link only to stable
documents. See catalog `general.md`.

## Hygiene

- No secrets or real credentials
- Prefer archive of superseded plans over delete
- Fix stale architecture / user-doc claims when you touch the area
- Do not recreate a living design changelog
