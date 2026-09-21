---
title: General process
read_when: Always for multi-step work — plans, slices, handoffs, taskforces, orchestrator, subagents, architecture vs patches, canonical APIs
order: 10
version: 4.1.0
---

# General Agent Guidelines

## Rule vocabulary

| Label | Meaning |
| --- | --- |
| **FIRM** | Must follow. Escalate or stop if you cannot. |
| **GUIDELINE** | Default. Override only with clear reason. |
| **MAY** | Optional. |

Unlabeled: treat security, git push/secrets, and SSH as **FIRM**; process/style as **GUIDELINE**.

## Clarity (FIRM)

Aim for ~**90%** confidence the next agent/human acts correctly. Do not shave tokens into ambiguity.

Agent↔agent text (plan Session notes, spawn notes, `priority.md`): **functionally detailed, unambiguous, succinct** — not “short” or “long.” No transcript dumps. Redundancy only for rare strong emphasis.

`AGENTS.md` is a **routing index** (when to open files under `agents/`). Full rules live in those files. Open them when triggers match.

## The handbook (FIRM)

`agents/` is the **agent handbook**. Policies (who may edit what, one home per fact) and procedures (how to run a plan, how to confirm acceptance) both live here. In prose, say **handbook**, not “the agents folder.”

Ownership is **declared in the file**, not by filename case. Filenames are lowercase except names required by an external standard (`README.md`, `AGENTS.md`).

There is **no** living design changelog. The target system is `agents/architecture.md`. Open rule conflicts and leftovers live in `agents/conflicts.md`. Retired decisions live in `agents/conflicts-resolved.md` and are not rules (Conflicts below). Gaps in the running code are **plans**, not a reason to rewrite the handbook. Git history and archived plans are the trail.

Do **not** recreate `HANDOFF.md`, `PRIORITY.md` (ALL-CAPS), `design.md`, or `agents/design/CHANGELOG.md` as living law.

### Human-owned files

These change only with **explicit permission in the current message**. Propose a patch and wait:

| File | Role |
| --- | --- |
| Repo-root `README.md` | Product README: install and usage only |
| `agents/user.md` | Who the human is and how to collaborate. Not product law |
| `agents/README.md` | How this handbook is run |
| `agents/project.md` | What the project is |
| `agents/architecture.md` | How it is built and how it runs (target) |
| `agents/acceptance.md` | When work is complete |
| `agents/general.md` | Project working rules (when present; amends this file) |
| `agents/documentation.md` | Project writing map (when present) |
| `agents/testing.md` | Project test map (when present) |

A project **MAY** name additional human-owned files (for example `host-constraints.md`). Those files state their own stricter permission. Architecture permission is not enough to edit a stricter file.

### Agent-owned files

Agents update these as part of ordinary work:

| File | Role |
| --- | --- |
| `agents/glossary.md` | Words |
| `agents/priority.md` | Ordered list of plans |
| `agents/conflicts.md` | **Active** rule conflicts, and **Leftovers** that lag a settled rule |
| `agents/conflicts-resolved.md` | Retired decisions. Append a row only. Rows are not rules. Do not delete the file or the section “These rows are not rules” |
| Plan **Session** section | Current status for the next agent on that plan |
| `agents/ideas/` | Parked ideas |

Plans under `agents/plans/` are **shared**: humans and agents both edit them. Goal, acceptance, and approach are human-readable product writing. Session notes are for the next agent on that plan.

## One home per fact (FIRM)

A rule lives in exactly one file. Other files may link to it. They must not restate it.

| Fact | Home |
| --- | --- |
| What the product is | `agents/project.md` |
| How it is built and how it runs | `agents/architecture.md` |
| When work is complete | `agents/acceptance.md` |
| What words mean | `agents/glossary.md` |
| How we test | `agents/testing.md` (project) / this catalog `testing.md` |
| Where writing lives | `agents/documentation.md` (project) / this catalog `documentation.md` |
| What to do next | `agents/priority.md` |
| Open rule conflicts (**Active**) and code or names lagging a settled rule (**Leftovers**) | `agents/conflicts.md` |
| Retired conflict decisions | `agents/conflicts-resolved.md` |
| How the conflicts system works, including that retired rows are not rules | This file, Conflicts |
| This piece of work | one file under `agents/plans/` |

`architecture.md` is the **target** system, not a snapshot of today's tree. When code lags that file, close the gap with a plan. Do not edit the handbook to match leftovers. If the architecture itself looks directionally wrong, stop that issue and meet — see `architecture.md` “This file can be wrong.”

## What is stone (FIRM)

**Stone** (product or architecture law) lives only in human-owned handbook files: `architecture.md`, `acceptance.md`, and any project-declared stricter files. Write it there **only when the human says to**. Each lock includes **why**: the user-visible problem, what was rejected, what it does, and what it does not apply to. A sentence without why is not a lock; stop and ask, or put it on the plan Session as exploration.

**Not stone:** chat (including “don’t do X” during a hunt), plan Session notes, `priority.md` quotes of chat, slice fences (“do not rename this file this slice”), and every row in `agents/conflicts-resolved.md`. A fence binds **that slice only**. The next agent must not copy it into architecture or priority as a standing veto. Retired conflict rows are decisions made at particular moments. They are not rules. Deleting that file, or the section that says the rows are not rules, does not make them rules. Full order: Conflicts below.

**Why:** exploratory fences got copied as architecture. They had no why, blocked honest facts, and the next agent papered over with a fallback. Development includes trying things and being wrong. Discovery updates the handbook in a meeting; it does not accumulate vetoes.

If a later fact contradicts a lock, stop that issue and meet. Do not hide the miss with a second path.

## Conflicts (FIRM)

This section is the one home for how conflicts work. `agents/README.md` repeats only the session-start sentence, because session start does not open this file. `agents/documentation.md`, when present, names the files and links here. Do not write a second procedure in those files.

**Active** in `agents/conflicts.md`: two living rules disagree (handbook vs handbook, or handbook vs another agent rule that is still in force), and a later agent could follow either one. Do not implement either side until the human picks. The row blocks only work that depends on it.

**Leftovers** in that file: code or an old name lags a rule that is not itself in dispute. The rule stays. The plan on `agents/priority.md` closes the gap. A leftover does not block unrelated work.

When two sources disagree (handbook vs handbook, handbook vs plan, plan vs plan, handbook vs code, handbook vs catalog), or when a leftover name is still taught as law:

1. Add a row to `agents/conflicts.md` in the same turn, even if you do not yet know the fix. Tell the human you found it. A fight between two living rules goes under **Active**. Code or an old name lagging a settled rule goes under **Leftovers**.
1. Handbook wins over plans, catalog, and leftovers. If the handbook looks wrong, stop and ask. Do not silently pick.
1. As soon as a leftover's fix can be named, write or extend a plan and put it on `agents/priority.md`. If a plan already owns the gap, link that plan on the row. Do not open a twin plan. An active row does not get an implementation plan until the human picks the side.
1. A scope fence (“do not rename this slice”) forbids the big rename. It does not license new identifiers or comments that teach the leftover word.
1. When the leftover is gone, or the handbook already says how to read it and no further hunt is queued, move the row to `agents/conflicts-resolved.md`. Record the leftover and the decision at that moment. Do not copy a living rule into that row. Do not leave a closed table in `agents/conflicts.md`.

### Resolved conflicts are not rules

Session-start sentence. `agents/README.md` repeats these words and does not add a second order:

> The rows in `conflicts-resolved.md` are not rules. They are decisions made at particular moments to iteratively shape the actual living rules in architecture and the rest of the handbook. Do not delete that file. Do not delete, weaken, or rewrite the section “These rows are not rules.” Removing that section does not turn the rows into rules. If that section is missing, restore it before any other edit to that file.

Living rules are `agents/architecture.md`, `agents/acceptance.md`, any project-declared stricter file, `agents/glossary.md` for words, and the selected OpSet document when the project has one. Architecture is a current belief and can change. When a resolved row and a living rule disagree, the living rule is what we believe now. A resolved row does not keep, restore, or block a behavior.

`agents/conflicts-resolved.md` is agent-owned so a retired row can be appended. That same ownership must not become a way to clear an inconvenient decision. Do not delete a row. Do not rewrite an old decision so that it reads as the current rule. When architecture changes later, leave the old decision as it was.

## Human-readable prose (FIRM)

Handbook files, plan goal/acceptance/approach, and plan Human checklists are written for a human who has not memorized the project.

- Full sentences. Name the actor.
- No decoder required. Do not explain the system as a trail of old ids.
- Links only to long-term stable documents. No links to short-lived chats, review threads, or session scratch.
- No references to old conversations as if they were law.

### Task ids in prose

Short ids (`D118`, plan slice names) are allowed.

In **human-readable files** (human-owned handbook files, `glossary.md`, plan goal/acceptance/approach/human, user docs): the **first** use of an id in that file must include the human-readable name.

Write: hide-place-show (`D118`). Do not write: `D118` alone.

In **agent working notes** (`priority.md`, plan Session sections): ids alone are fine if that plan already named the work. Prefer the name once per file anyway.

## User Questions (FIRM)

Never use the `ask_user_question` tool.
If something is truly blocking, ask in normal chat with full context.
After we discuss, write the decision down and continue from that written result.
Do not re-ask or ignore prior answers; only re-ask if new context changed the meaning of the original answer.

## Residue (FIRM)

Before finishing: remove temp paths, debug prints, failed-attempt code, fake fixtures, and live-env residue you added. Failed attempts: delete dead code everywhere it landed.

## Backwards compatibility (GUIDELINE)

During active development, do **not** preserve backwards compatibility by default. Prefer clean breaks unless real users depend on a released surface.

## Architecture over patches (FIRM)

Prefer a strong architectural fix when the failure class will recur or band-aids are stacking. Temporary only if the operator **explicitly** asks for temp/stopgap.

If a warranted redesign looks **very expensive** (millions+ tokens, multi-session rewrite) vs a small patch: **stop**, present options, and wait for an architecture meeting. Do not silently burn a huge redesign.

When the real fix lands, remove competing crutches in the same effort when safe.

## Canonical APIs (FIRM)

Use the project’s existing API/contract for a job. Do **not** hand-roll a
parallel path (direct field writes, one-off loops, a local helper that
duplicates a named primitive).

If the existing API is insufficient:

1. Extend that API (or add a sibling on the same type/module).
2. Convert callers to it.
3. Then use it.

Hand-roll only when no contract exists yet **and** extending would be a large
unrelated redesign — say so in the plan note. A one-off that “works here” but
bypasses the shared path is a bug class: the next call site will drift
(order swaps, missed cleanup, skipped invariants).

## Optional features in dev (FIRM)

When working on an optional feature, **enable it** in the local/dev environment for that session. Record how in the plan Session. Dev-on ≠ ship default-on.

## Plans (FIRM — all work is a plan)

**All work is a plan.** Colloquial “task” means a bite-sized **slice inside** a
plan (sometimes the only slice). There is **no** second top-level work type and
**no** peer queue at `agents/tasks/`.

**Execution queue:** `agents/priority.md` lists plan paths. Agents pick next
work from there. Session notes live **on the plan**, not in a separate handoff file.

When the operator says “plan” they mean either ordinary English (“I was
planning…”) or the durable in-repo system under `agents/plans/` (“Create a plan
to…”). **Never** use Grok `/plan` mode (`enter_plan_mode` /
`~/.grok/sessions/…/plan.md`); that scratch is not a handoff. Plans are authored
in conversation and architecture meetings and stored under `agents/plans/`.

| Rule | Detail |
| --- | --- |
| **Source of truth** | **FIRM.** `agents/plans/<plan>.md` is the durable spine. Operators and agents look there **first** whenever anyone says “the plan” / names a plan. |
| **Working weight** | Optional detail under `agents/plans/<id>/` as needed. |
| **In-repo only** | **FIRM.** Keep plans in this repo’s `agents/plans/`; cross-repo work → that repo’s `agents/plans/`. Do **not** leave the only copy under `~/.grok/sessions/`, `/tmp`, or outside the repo unless the **current** user message explicitly says to. |
| **Grok `/plan` mode** | **FIRM — never.** Do **not** call `enter_plan_mode` / Grok `/plan`. Do not treat session `plan.md` as handoff. |
| **Archive (completed)** | → `agents/plans/archived/completed/` |
| **Archive (abandoned)** | → `agents/plans/archived/abandoned/` |
| **Not archive-inside-self** | Do **not** use `plans/<id>/completed/` as the archive root for the whole plan. Per-plan `completed/` dirs may hold in-flight slice history until migrated. |
| **Template** | Use `agents/plans/_TEMPLATE.md`. |
| Major redesigns | Plan first under `agents/plans/`; implement after approval (conversation / architecture meeting) |
| Plan reshape discovery | Stop and ask |
| Progress note | Overwrite the plan **Session** when code changes |
| Status | `draft` / `active` / `waiting` / `accepted` / `abandoned` |
| Optional | Skip unless user includes optional |
| Waiting | Human section on the plan; labeled in `priority.md` |

The plan holds approach, plan-local acceptance, and session notes. It is **not** a second architecture file.

When a plan is accepted, archive it. If some of its acceptance should apply to all future work, ask to promote those items into `acceptance.md`.

If a new plan would change shipped behavior, amend `acceptance.md` (with permission) in the same effort. If it would change how the system is built, amend `architecture.md` the same way.

### Other archives

`agents/archive/INDEX.md` + `entries/` may hold searchable ship summaries.
Do not treat `plans/archived/` trees as active work unless `priority.md`
names a hunt. Prefer archive over delete; delete only stubs/dupes/junk.

## Ideas (FIRM)

Park ideas in `agents/ideas/` with a category: product, architecture, tooling, or needs an architecture meeting. An idea is not a plan until it has a goal and acceptance.

After an architecture meeting: clear obsolete / decided / implemented ideas.

## Completion

A plan is complete when:

1. Its own acceptance items are met.
2. The gestures in `agents/acceptance.md` still hold, confirmed as that file describes.

Unit tests support that confirmation. They are not a substitute for it.

## Human waits

**Real** human work only — not agent laziness.

If only a human can proceed, write that on the **plan**: a **Human** section with checkboxes, read top to bottom. Do not put agent hunt recipes there.

Label the plan in `agents/priority.md` as a human blocker so the next agent does not start implementing. Other work continues unless that plan is the only active item.

There is **no** separate blockers directory as the unit of work. A human wait is plan state. Leftover `agents/blockers/` trees may still exist in older repos; fold waits onto the owning plan when you touch them. Full audience rules: catalog **`documentation.md`** § Audience.

| Rule | Kind |
| --- | --- |
| Hard only when agent must not proceed alone | **FIRM** |
| Make human work easy (short steps + `- [ ]` checklist) | **FIRM** |
| Prep first (install/config/branch if you can) — record on the plan Session | **FIRM** |
| Never mark human steps done yourself | **FIRM** |
| Fake blockers forbidden | **FIRM** |
| One-line “why human-only”; no agent-prep section in the Human checklist | **FIRM** |

## Subagents

Subagents inherit these rules. A child does not get a looser license to edit human-owned files or to restate architecture in a side note.

### Orchestrator + taskforces (when plans / priorities)

On plan or priority work, the **main agent is the orchestrator**: assign work to
subagents; do not do large implementation yourself when a taskforce fits.

| Rule | Detail |
| --- | --- |
| Who spawns | **Only** top-level orchestrator; children cannot spawn |
| Default shape | **Single-agent** taskforce (one implementer per assignment) |
| Batching | **MAY** give one agent several related slices when one session is likely cheaper than multiple handoffs |
| Parallel | **Only when safe** (no shared-file races, no conflicting branch edits, independent acceptance). Otherwise **serial** |
| A/B (expensive) | **Only when necessary** — major architecture, high-stakes decisions, or when a separate verifier is clearly worth the cost. Not the default for ordinary implement slices |
| A then B | When A/B is used: implement → verify; **never** parallel A/B |
| Explore (on demand) | **MAY** use a short-lived read-only explorer for cold/unfamiliar scope. Prefer **explore+implement in one agent** for ordinary slices |
| Explore output | Write findings only into the **active** plan Session (entry points, proven vs guessed, traps). **No** standing repo-wide explore digest |
| Fresh agents | New subagent(s) per assignment; no `resume_from` for baggage (unless operator asks) |
| Branch | **Default master** unless isolation required (see git.md) |
| Handoff | Overwrite the plan Session (complete+succinct); no transcript paste into next prompt |
| Budget | Stop starting new slices ~300K orchestrator tokens |
| Max A/B rounds | 5 A→B when A/B is in use; then escalate |
| DESIGN-FLAW | Stop; architecture discussion; no wrap-up commit |
| Model | Grok + high reasoning unless user says otherwise |
| Eligible | Required active plans; not optional / human-waiting |

**Cost stance (GUIDELINE):** A/B doubles agent work. Prefer one capable implementer +
orchestrator review of disk notes/diff. Escalate to A/B for big irreversible
choices or when independent verification is the acceptance path.

**Begin** (no plan named): read `priority.md` + the first plan it names.

Wrap-up on success: residue → plan Session → docs as needed → tests → commit/push per git.md.

## Agents layout ownership (FIRM)

Root `AGENTS.md` is **generated** (`agents build` / `python3 agents.py build`) —
a routing index (TOC + hard kernel), **not** the rulebook. Do not edit it by
hand; do not gitignore it (Grok skips gitignored project instructions).

| Path | Role | Who edits |
| --- | --- | --- |
| **`AGENTS.md`** | Transpiled index: hard kernel + session/queue pointers + guideline TOC | **Only** `agents build` |
| **Repo-root `README.md`** | Product install and usage | **Human** — explicit permission |
| **`agents/README.md`**, **`project.md`**, **`architecture.md`**, **`acceptance.md`** | Handbook (what / how / done) | **Human** — propose; apply with permission |
| **`agents/general.md`**, **`documentation.md`**, **`testing.md`** (when present) | Project working / writing / test map | **Human** — propose; apply with permission |
| **`agents/glossary.md`** | Words | **Agents** |
| **`agents/priority.md`** | Ordered list of plans | **Agents** |
| **`agents/user.md`** | Who the human is and how to collaborate. Not product law | **Human** |
| **`agents/conflicts.md`** | Active rule conflicts, and leftovers that lag a settled rule | **Agents** |
| **`agents/conflicts-resolved.md`** | Retired decisions. Not rules. Append a row only. Do not delete the file or the section “These rows are not rules” | **Agents** |
| **`agents/plans/`**, **`plans/archived/`** | Plans + completed/abandoned archives | Shared |
| **`agents/ideas/`** | Parked ideas | Agents + project |
| **`agents/installed/*`** | Portable guideline bodies from the **agents-catalog** | **Only** `agents install` / `agents update` — **never** hand-edit |
| **`agents/<same-rel-as-installed>`** | **Extension** (default) — amends installed; **wins on conflict with catalog** | Prefer this for project deltas. Handbook files still win over catalog. Fold portable improvements into the catalog. |
| **`agents/<stem>.extend.md`** | Explicit extension (same rules) | Do **not** also keep same-name or `*.override.md` for that id |
| **`agents/<stem>.override.md`** | **Override** — replaces installed for that id | Rare durable fork only. Prefer extension or a catalog fix. |

Exactly **one** of the three layer forms may exist per installed file.
`agents update` **errors** if they are mixed.

On conflict with `agents/installed/`, **handbook files win**.

**Hard kernel** (always-on rows at the top of `AGENTS.md`) lives in catalog
**`always.md`** → installed as `agents/installed/always.md` → **inlined** by
`agents build`. Composer does **not** own policy strings. Kernel points at full
rules in `security.md`, `git.md`, etc. Open those when the domain matches.

**Split-brain ban:** do not maintain a second full copy of a catalog guideline
under `agents/` “just because.” Extend with deltas, or update the catalog (then
`agents update`). `agents reclaim` pulls accidental `installed/` edits into the
default **extension** path — then fold into catalog or keep as a deliberate
extend/override.

After install/update/override changes: `agents build`.
