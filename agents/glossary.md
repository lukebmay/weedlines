# Glossary

When to use: A word you are about to write.

**Owner:** agent. Agents read and write this file. Keep it human-readable.

Words used across the handbook. Product-specific terms belong in the
project section below. Process terms are shared across repos that use
this catalog.

If two handbook sentences still make sense after swapping two of these
words, rewrite them.

Leftover identifiers still taught as law go in
[`conflicts.md`](./conflicts.md). Names already retired are listed
in [`conflicts-resolved.md`](./conflicts-resolved.md). Those rows
are not rules. This file stays
the law for the target words.

## Handbook

| Word | Meaning |
| --- | --- |
| **handbook** | The `agents/` directory: policies and procedures for agents operating on this codebase. In prose, say handbook, not “the agents folder.” |
| **stone** | The current guide. Architecture records what has worked and warns about what has failed. Acceptance records the product checks. Written when the human says so. An old sentence is not kept because it is old. Not a history, and not a ban on a better design. Chat, plan notes, `priority.md` quotes, and rows in `conflicts-resolved.md` are not stone. |
| **leftover** | Code or an old name that lags a settled handbook rule. Track it under **Leftovers** in `conflicts.md`. Do not mint more of it. |
| **active conflict** | Two living rules disagree. Track it under **Active** in `conflicts.md`. Do not implement either side until the human picks. |
| **one home per fact** | A rule lives in exactly one file. Other files link; they do not restate. |
| **catalog** | Portable guideline fragments under `agents/installed/`, refreshed by `agent-handbook`. Handbook files win on conflict. |
| **extension** | Project file at `agents/<same-path-as-installed>` (or `*.extend.md`) that amends a catalog file. |
| **override** | Project file `agents/<stem>.override.md` that replaces an installed catalog file for that id. Rare. |
| **human-owned** | File agents may propose edits to; apply only with explicit permission in the current message. |
| **agent-owned** | File agents update as ordinary work (`glossary.md`, `priority.md`, `conflicts.md`, `conflicts-resolved.md` append-only, the note on the task). |
| **explicit** | Permission word in the **current** user message for `ssh`, `scp`, `sftp`, a remote login, root, or using another program as a back door onto a machine. Not required for `git push`, `git fetch`, or `git pull` the user asked for. See catalog `security.md`. |

## Work

| Word | Meaning |
| --- | --- |
| **plan** | A directory `agents/plans/<name>/`. The entry is `plan.md`. The shape is `agents/plans/README.md`. A flat file is the old shape. |
| **task** | Work one session can finish. `plans/<name>/tasks/<bucket>/<task>/task.md`. Not a second queue. |
| **slice** | An older word for a task. Not a second work type. |
| **handoff** | The note on that task for the next agent. The developer writes what changed, why, and how it was checked. The rule is `agents/plans/README.md`. |
| **Session** | Old name for the handoff. Not stone. The note lives on `task.md`. |
| **Human** | A `waiting` task whose blocker is a person. The task names the blocker. Do not call it a human wait when an agent can do the work. |
| **Approach** | How this plan is built. Do not restate global architecture here. |
| **Goal** | What this plan makes true. |
| **Acceptance** | Checks that must hold for the plan (local) or for any work (product file `acceptance.md`). |
| **priority** | `agents/priority.md`: the queue of plans, ordered by rank. A plan's own `priority.md` lists that plan's tasks. Agent-owned. |
| **rank** | A plan's priority number. 5 is top, 4 is high, 3 is medium, 2 is low, and 1 is optional. Who may set each number is `agents/plans/README.md`. |
| **version group** | A range of tool versions that share one handbook shape. The ranges and the migration from one group to the next are `agents/versions.md`. |
| **orchestrator** | The role Orchestrate assigns. Speaking does not assign it. It reads the whole architecture. It does not choose the solution. It accepts a delegate's unit of work, or it says why and sends that agent back or assigns another delegate. The procedure is `agents/roles/orchestrator.md`. |
| **delegate** | An agent the orchestrator starts. The prompt says so. It reads the files the brief names. It does not start other agents. |
| **role** | The kind of work. The prompt assigns it. A file cannot assign a role to the agent who merely opened it. The roles with a process are orchestrator, delegate, developer, code reviewer, architect, and maid. |
| **developer** | The role that makes the change. It writes a short note on `task.md`. It does not change the status, move the directory, write the `cr-` file, or start the reviewer. |
| **code reviewer** | The role that reads the change and writes `cr-01.md`, `cr-02.md`, and so on in the task directory, then updates `task.md`. The orchestrator starts it. |
| **architect** | The role that compares one directory plan to the guide and updates its tasks. A flat plan file is the old shape. It stops and does not invent `tasks/` unless the task says to translate. |
| **maid** | The role that makes plan files match. She does not choose the next product work and does not move archives. |
| **CR** | `cr-01.md`, `cr-02.md`, and so on, in the task directory. The code reviewer writes them. The developer does not. The orchestrator does not read them. |
| **brief** | The assignment: a role, the task path, the checks, and the architecture files that are the start. Open a further file when the task needs it, as [`roles/delegate.md`](roles/delegate.md) says. The brief does not paste a role's process. |
| **panel** | Readers asked to examine one question. The orchestrator accepts or sends back a unit of work. The rule is `agents/roles/orchestrator.md`. |
| **domain notes** | `agents/domains/<name>.md`. Current grievances, conflicts, and recurring problems for one area. Remove a line that is no longer true. Not stone. |
| **idea** | Parked thought in `agents/ideas/`. Not a plan until it has a goal and acceptance. |
| **wrap-up** | End of a successful slice: residue, notes, tests, commit/push per `git.md`. |
| **residue** | Temp paths, debug prints, failed-attempt code, fake fixtures, live-env leftovers the agent added. Remove before finishing. |

## Product files

| Word | Meaning |
| --- | --- |
| **architecture** | `agents/architecture.md` is the index and how the parts fit. Each part lives under `agents/architecture/` when that directory exists. Until then, `architecture.md` is the whole guide. The guide of what has worked and what has failed. Not a snapshot, not a history, and not a ban on a better design. Human-owned. When it looks wrong, stop and meet. |
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
| `HANDOFF.md` as the start-here file | The note on **task.md** |
| `PRIORITY.md` (ALL-CAPS) as the queue | **priority.md** |
| A separate `blockers/` item as the unit of work | A **waiting** task that names the blocker |
| A flat file as the plan | `plans/<name>/plan.md` |
| Chat “don’t do X” as architecture | A guide sentence **with why** in architecture, or a slice fence on the plan |
| A/B taskforce, taskforce, verifier, review pair, or implementer | **delegate** with a **role** (`developer`, `code reviewer`, or a common role) |
| A confidence number as a review | Defects, or a statement that none remain |

## Project words

Product words live in [`architecture/glossary.md`](./architecture/glossary.md).
Add a word there. Do not copy it into this table.
