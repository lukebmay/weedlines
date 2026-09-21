---
title: Documentation
read_when: Writing architecture, user docs, human-facing checklists, or choosing where “why” lives
order: 60
version: 4.1.0
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
| Actions only | Warnings and agent-only procedure belong in the plan Session — not the human checklist |

**Agent-facing** files (`priority.md`, plan Session notes) stay
functionally detailed for the next agent. That density is wrong on a
human checklist.

## Where writing lives

| Kind | Place |
| --- | --- |
| Product README (install and usage) | Repo-root `README.md`. **Human-owned.** Agents read it; write only with explicit permission in the current message. Anything beyond install and basic usage belongs in `docs/`. |
| What the product is | `agents/project.md` |
| How it is built and how it runs (target) | `agents/architecture.md` |
| Who the human is and how to collaborate | `agents/user.md`. Not product law |
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

Do not add a parallel architecture, glossary, or acceptance in a plan,
priority note, conflict row, or catalog file. How a conflict row is
written, and why a retired row is not a rule: catalog `general.md`
Conflicts.

Architecture and acceptance locks include **why** in the same file
(user-visible problem, rejected alternatives, what the lock does, what
it does not apply to). Architecture can be wrong; stop and meet rather
than paper over. Chat, plan Session, and `priority.md` are not stone.
Full rule: catalog **`general.md`** § What is stone.

User-visible behavior changes update `docs/user/` in the same effort.

Plan session notes are for the current plan. They are not a second
architecture file.

## Architecture writing (FIRM)

What *is* written must be **crystal clear**. A later agent or human must
act correctly **without guessing**. Unclear architecture is a bug: people
will treat a vague lock as a permanent veto and ship around it.

| Rule | Detail |
| --- | --- |
| **No room to interpret** | If two readers can honestly disagree on who/what/when, rewrite. If a sentence still works after swapping two domain words, it is too vague |
| **Name the actor** | Say **who** does the thing. Do not say “write”, “observe”, “desired”, “recompute” unless the sentence also says **which layer and which value** |
| **Context in the architecture** | Every lock in `agents/architecture.md` includes: the user-visible problem, what was rejected and why, what the lock **does**, and what it **does not** apply to |
| **Plans inherit this** | Plan spines, meeting notes, and operation docs use the same bar. Session paraphrase is not a substitute |

### Cross-lock update (FIRM)

When you change a **core element** that another lock, plan, or glossary
uses (a word, invariant, identity, …):

1. Find every architecture section, plan, and glossary entry that
   depends on it.
1. Update, supersede, or translate those **in the same effort**.
1. If you cannot: **stop and ask**. Do not ship a lock that silently
   contradicts another.

This is the same-effort rule for **design dependencies**. Leaving a
dependent lock stale is how features disagree and block progress.

## Task ids

In this file and every other human-readable handbook or plan section,
the first use of a short id includes the human-readable name. See
catalog **`general.md`**.

## Links

Link only to long-term stable documents in this handbook or the project
repo. Do not link ephemeral chats, review threads, or session scratch.

## Hygiene

- No secrets or real credentials
- Prefer archive of superseded plans over delete
- Fix stale architecture / user-doc claims when you touch the area
- Do not recreate a living design changelog
