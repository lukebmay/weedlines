# Agent handbook

How this project is run. The audience is agents operating on the
codebase, and the human who must be able to read and correct those
rules.

This system exists because agents change the product. It is not a
general staff handbook that happens to mention bots. **Policies** (who
may edit what, one home per fact) and **procedures** (how to run a
plan, how to confirm acceptance) both live here; neither name covers
the whole thing, so this directory is the **agent handbook**.

On disk this handbook is `agents/` in the project repo (the `agents`
CLI and root `AGENTS.md` compose step use that path). In prose, say
**handbook**, not “the agents folder.”

Read these in order when starting work:

1. [`project.md`](./project.md) — what this project is
2. [`architecture.md`](./architecture.md) — how it is built and how it runs
3. [`glossary.md`](./glossary.md) — words
4. [`conflicts.md`](./conflicts.md) — leftover names and contradictions
5. [`acceptance.md`](./acceptance.md) — when work is complete
6. [`priority.md`](./priority.md) — what to do next
7. The active plan named in priority

## Ownership

Ownership is declared in the file, not by filename case. Filenames are
lowercase except names required by an external standard (`README.md`,
`AGENTS.md`).

| File | Owner | Agents |
| --- | --- | --- |
| [`../README.md`](../README.md) (product README) | Human | Read; write only with explicit permission |
| [`project.md`](./project.md) | Human | Propose edits; apply only with permission |
| [`architecture.md`](./architecture.md) | Human | Propose edits; apply only with permission |
| [`acceptance.md`](./acceptance.md) | Human | Propose edits; apply only with permission |
| [`general.md`](./general.md) (when present) | Human | Propose edits; apply only with permission |
| [`documentation.md`](./documentation.md) (when present) | Human | Propose edits; apply only with permission |
| [`testing.md`](./testing.md) (when present) | Human | Propose edits; apply only with permission |
| [`glossary.md`](./glossary.md) | Agent | Words |
| [`priority.md`](./priority.md) | Agent | Ordered list of plans |
| [`conflicts.md`](./conflicts.md) | Agent | Leftover names and contradictions |
| [`plans/`](./plans/) | Shared | One plan per piece of work |

A **plan is the unit of work**. It holds the goal, the plan’s own
acceptance, the approach, and current session notes.

Ideas belong in [`ideas/`](./ideas/). Classify them (product,
architecture, tooling, needs an architecture meeting) before they
become plans. A plan that would change shipped behavior updates
[`acceptance.md`](./acceptance.md) in the same effort, with permission.

There is no living design changelog. The target system is
[`architecture.md`](./architecture.md). Leftover names and
contradictions live in [`conflicts.md`](./conflicts.md); resolving
them is plan work on [`priority.md`](./priority.md). Gaps in the
running code are plans, not a reason to rewrite the handbook. Git
history and archived plans are the trail.

## Also here

| Path | Role |
| --- | --- |
| [`testing.md`](./testing.md) (when present) | How we test, including regressions |
| [`documentation.md`](./documentation.md) (when present) | Where writing lives |
| [`general.md`](./general.md) (when present) | Project working rules |
| [`conflicts.md`](./conflicts.md) | Leftover names and contradictions |
| [`plans/archived/`](./plans/archived/) | Finished or dropped plans |
| [`installed/`](./installed/) | Portable catalog guidelines |
| [`AGENTS.md`](./AGENTS.md) | Handbook routing map. Repo-root `AGENTS.md` is composed from this handbook by `agents build` |

Portable catalog files under [`installed/`](./installed/) are refreshed
with the `agents` CLI. On conflict, **this handbook wins**.
