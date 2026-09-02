---
title: General process
read_when: Always for multi-step work — plans, slices, blockers, handoffs, taskforces, orchestrator, subagents, architecture vs patches, canonical APIs
order: 10
version: 3.3.0
---

# General Agent Guidelines

## Rule vocabulary

| Label | Meaning |
| --- | --- |
| **FIRM** | Must follow. Escalate or stop if you cannot. |
| **GUIDELINE** | Default; override only with clear reason. |
| **MAY** | Optional. |

Unlabeled: treat security, git push/secrets, and SSH as **FIRM**; process/style as **GUIDELINE**.

## Clarity (FIRM)

Aim for ~**90%** confidence the next agent/human acts correctly. Do not shave tokens into ambiguity.

Agent↔agent text (handoffs, spawn notes, PRIORITY, session notes): **functionally detailed, unambiguous, succinct** — not “short” or “long.” No transcript dumps. Redundancy only for rare strong emphasis.

`AGENTS.md` is a **routing index** (when to open files under `agents/`). Full rules live in those files. Open them when triggers match.

## Design (FIRM)

| Layer | Role |
| --- | --- |
| **`agents/design.md`** | **Guiding light** — high-level picture, key inner workings, important tech choices + reasoning. **Not** a comprehensive novel of every decision. Optional until the first design meeting. |
| **`agents/design/CHANGELOG.md`** | Thin dated history / supersessions (was `docs/DECISIONS.md`; **agent-managed** CAPS) |
| **`docs/user/*`** | Human-facing write-ups after meetings — not a substitute for `agents/design.md` |
| Accepted plan / meeting locks | Bind until superseded |

| Rule | Detail |
| --- | --- |
| **Newest wins** | The **most recent** design meeting lock or CHANGELOG row for a topic **supersedes** older rows, plan prose, and handoff guesses |
| **Mark history** | When replacing a decision: mark the old CHANGELOG row superseded, add a **new** dated row — do not silently rewrite history |
| **Read order** | Current `agents/design.md` for the topic → latest CHANGELOG / meeting lock → then older plan text |
| **Conflict** | If code and an older doc disagree, believe **code + newest design**; fix the stale doc in the same effort when you touch the area |

`agents build` may inline `agents/design.md`’s **`## Overview`** (or **`## AGENTS.md View`**) into `AGENTS.md`. Keep that section small (token budget).

### CAPS files are agent-managed (FIRM)

Filenames that are **ALL CAPS** under `agents/` (e.g. `HANDOFF.md`, `PRIORITY.md`, `CHANGELOG.md`, generated `AGENTS.md`) are **agent-managed**. Humans *may* edit them; that is not the intended workflow. Agents own updates to these files.

**`agents/project.md`** is the primary **user** hand file (conventions/stack). Lowercase `design.md` is agent-primary / optional until a design meeting creates it.

### Plan start gate (FIRM)

Before implementing from a plan:

1. Align the plan with **current** `agents/design.md` when it exists.
2. Larger date gap between plan and design ⇒ more skepticism.
3. Conflict ⇒ **stop and ask**; **design wins**.
4. Translate steps when acceptance no longer maps cleanly — do not execute stale steps that contradict a newer lock.

### Design meeting hygiene (FIRM)

When a design meeting lands a new direction:

1. **Finish-before-redesign** — ask what open work must finish **before** the new design starts (record in `agents/design.md`).
2. **Same effort:** update, cancel, or translate affected **plans** and **ideas**; create/update `agents/design.md` if missing.
3. Update **`docs/user/*`** when the design changes **user-visible** behavior (not RC-schedule-gated).

### Ideas (FIRM cleanup)

Prefer `agents/ideas/` over a single mega-file when volume warrants. After every design meeting: clear obsolete / decided / implemented ideas.

### Optional leftovers (GUIDELINE → FIRM after two meetings)

Soft leftovers on a **shipped** plan: after **two design meetings** without pickup → close (`wontfix` / done) or spin a **new** thin plan. Do not leave soft-open forever.

## User Questions (FIRM)

Never use the `ask_user_question` tool.
If something is truly blocking, ask in normal chat with full context.
After we discuss, write the decision down and continue from that written result.
Do not re-ask or ignore prior answers; Only re-ask if new context changed the meaning of the original answer.

## Residue (FIRM)

Before finishing: remove temp paths, debug prints, failed-attempt code, fake fixtures, and live-env residue you added. Failed attempts: delete dead code everywhere it landed.

## Backwards compatibility (GUIDELINE)

During active development, do **not** preserve backwards compatibility by default. Prefer clean breaks unless real users depend on a released surface.

## Architecture over patches (FIRM)

Prefer a strong architectural fix when the failure class will recur or band-aids are stacking. Temporary only if the operator **explicitly** asks for temp/stopgap.

If a warranted redesign looks **very expensive** (millions+ tokens, multi-session rewrite) vs a small patch: **stop**, present options, open a **hard** design blocker. Do not silently burn a huge redesign.

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

When working on an optional feature, **enable it** in the local/dev environment for that session. Record how in the plan/handoff. Dev-on ≠ ship default-on.

## Plans (FIRM — all work is a plan)

**All work is a plan.** Colloquial “task” means a bite-sized **slice inside** a
plan (sometimes the only slice). There is **no** second top-level work type and
**no** peer queue at `agents/tasks/`.

**Execution queue:** `agents/PRIORITY.md` (+ `agents/HANDOFF.md`) lists plan
paths and optional `plan#slice` markers. Agents pick next work from there — not
from a tasks directory.

When the operator says “plan” they mean either ordinary English (“I was
planning…”) or the durable in-repo system under `agents/plans/` (“Create a plan
to…”). **Never** use Grok `/plan` mode (`enter_plan_mode` /
`~/.grok/sessions/…/plan.md`); that scratch is not a handoff. Plans are authored
in conversation and design meetings and stored under `agents/plans/`. The
shellrc `bin/grok` wrapper injects `--no-plan` by default (D063); pass
wrapper-only `--plan` only when intentionally opting into Grok plan mode.

| Rule | Detail |
| --- | --- |
| **Source of truth** | **FIRM.** `agents/plans/<plan>.md` is the durable spine. Operators and agents look there **first** whenever anyone says “the plan” / names a plan. |
| **Working weight** | Optional detail under `agents/plans/<id>/` as needed. |
| **In-repo only** | **FIRM.** Keep plans in this repo’s `agents/plans/`; cross-repo work → that repo’s `agents/plans/`. Do **not** leave the only copy under `~/.grok/sessions/`, `/tmp`, or outside the repo unless the **current** user message explicitly says to. |
| **Grok `/plan` mode** | **FIRM — never.** Do **not** call `enter_plan_mode` / Grok `/plan`. Do not treat session `plan.md` as handoff. |
| **Archive (completed)** | → `agents/plans/archived/completed/` |
| **Archive (abandoned)** | → `agents/plans/archived/abandoned/` |
| **Not archive-inside-self** | Do **not** use `plans/<id>/completed/` as the archive root for the whole plan. Per-plan `completed/` dirs may hold in-flight slice history until migrated. |
| Major redesigns | Plan first under `agents/plans/`; implement after approval (conversation / design meeting) |
| Plan reshape discovery | Stop and ask |
| Progress note | Overwrite one note when code changes (on the **repo** plan file or its working dir) |
| Status (slices) | `ready` / `next` / `in progress` / `blocked` / `optional` / `draft` |
| Optional | Skip unless user includes optional |
| Blocked | Requires linked **hard** human blocker |
| Draft | Not a stop if the next required slice has enough plan scope — refine + implement |

### Plan spine template

```markdown
# plan-id — Title

**Status:** Accepted | in progress | draft | …
**Branch:** master (default) | plan/… only if isolated
**Blocker:** (none) | agents/blockers/B-….md
**Updated:** YYYY-MM-DD

## Goal
## Acceptance
- [ ] …

## Implementation slices
| Slice | What | …
| **P1** | … |

## Context for the next agent (complete + succinct)
- Paths/symbols · Proven · Failed+why · Enable/test · Risks

## Session note
…
```

### Other archives

`agents/archive/INDEX.md` + `entries/` may hold searchable ship summaries.
Do not treat `plans/archived/` trees as active work unless PRIORITY/HANDOFF
names a hunt. Prefer archive over delete; delete only stubs/dupes/junk.

## Human blockers

**Real** human work only — not agent laziness.

Blocker files are **human-facing**. Write them for a human reading top→bottom
and answering inline (checkboxes). Full audience rules: catalog
**`documentation.md`** § Audience. Agent prep, hunts, and “done when”
restatements live in HANDOFF / plan notes — **not** in the blocker body.

| Difficulty | Behavior |
| --- | --- |
| **hard** (default if omitted) | Required path stopped; plan/slice `blocked`; taskforces skip |
| **soft** | Optional reminder; does not stop unrelated work |

(`**Severity:**` on older blockers = same field; prefer **Difficulty** on new ones.)

| Rule | Kind |
| --- | --- |
| Hard only when agent must not proceed alone | **FIRM** |
| Make human work easy (short steps + `- [ ]` checklist) | **FIRM** |
| Prep first (install/config/branch if you can) — record in HANDOFF | **FIRM** |
| Never mark human steps done yourself | **FIRM** |
| Fake blockers forbidden | **FIRM** |
| One-line “why human-only”; no agent-prep section in the blocker | **FIRM** |

Kinds: design · permission · credentials · expensive-test · verify · data-only-human.
(Do not pile redundant kind tags like `verify · physical`.)

```markdown
# B-short-id — Title
**Status:** open
**Difficulty:** hard | soft
**Owner:** human
**Kind:** design | …
**Plan:** …
**Unblocks:** agents/plans/… (or plan#slice)
**Priority:** P0
**Created:** YYYY-MM-DD
**Updated:** YYYY-MM-DD

## Why this is human-only
(one short sentence)

## What the human must do
1. …
1. …
   - [ ] …
```

## Handoffs (FIRM)

| Path | Role |
| --- | --- |
| `agents/HANDOFF.md` | Cross-session start-here |
| Plan session notes | Cold-continue for that plan / slice |
| `agents/PRIORITY.md` | Ordered next work (plan paths / `plan#slice`) |

Functionally complete + unambiguous + succinct. Overwrite, don’t pile. Exploration findings that prevent rescans belong on disk.

### Orchestrator + taskforces (when plans / priorities)

On plan or priority work, the **main agent is the orchestrator**: assign work to
subagents; do not do large implementation yourself when a taskforce fits.

| Rule | Detail |
| --- | --- |
| Who spawns | **Only** top-level orchestrator; children cannot spawn |
| Default shape | **Single-agent** taskforce (one implementer per assignment) |
| Batching | **MAY** give one agent several related slices when one session is likely cheaper than multiple handoffs |
| Parallel | **Only when safe** (no shared-file races, no conflicting branch edits, independent acceptance). Otherwise **serial** |
| A/B (expensive) | **Only when necessary** — major design/architecture, high-stakes decisions, or when a separate verifier is clearly worth the cost. Not the default for ordinary implement slices |
| A then B | When A/B is used: implement → verify; **never** parallel A/B |
| Explore (on demand) | **MAY** use a short-lived read-only explorer for cold/unfamiliar scope. Prefer **explore+implement in one agent** for ordinary slices |
| Explore output | Write findings only into the **active** plan handoff (entry points, proven vs guessed, traps). **No** standing repo-wide explore digest |
| Fresh agents | New subagent(s) per assignment; no `resume_from` for baggage (unless operator asks) |
| Branch | **Default master** unless isolation required (see git.md) |
| Handoff | Overwrite disk notes (complete+succinct); no transcript paste into next prompt |
| Budget | Stop starting new slices ~300K orchestrator tokens |
| Max A/B rounds | 5 A→B when A/B is in use; then escalate |
| DESIGN-FLAW | Stop; design discussion; no wrap-up commit |
| Model | Grok + high reasoning unless user says otherwise |
| Eligible | Required ready/next/in-progress plans/slices; not optional/hard-blocked |

**Cost stance (GUIDELINE):** A/B doubles agent work. Prefer one capable implementer +
orchestrator review of disk notes/diff. Escalate to A/B for big irreversible
choices or when independent verification is the acceptance path.

**Explore stance (GUIDELINE):** Explorer *passes* yes; explorer *literature* no.
Skip a separate explore step when the plan already scopes paths, the area is
recently known, or the implementer will re-walk the same tree anyway. Summaries
earn tokens only when they block a re-scan for **this** work — overwrite or drop
them with the plan.

**Begin** (no plan named): read PRIORITY + blockers → next eligible required work
→ single-agent (or rare A/B) taskforces until budget/done → report open blockers.

Wrap-up on success: residue → notes → docs as needed → tests → commit/push per git.md.

## Agents layout ownership (FIRM)

Root `AGENTS.md` is **generated** (`agents build` / `python3 agents.py build`) —
a routing index (TOC + hard kernel), **not** the rulebook. Do not edit it by
hand; do not gitignore it (Grok skips gitignored project instructions).

| Path | Role | Who edits |
| --- | --- | --- |
| **`AGENTS.md`** | Transpiled index: hard kernel + session/queue pointers + guideline TOC | **Only** `agents build` (CAPS / generated) |
| **`agents/project.md`** | Project-specific conventions / stack | **User** — only required hand-fill; **never** from catalog |
| **CAPS under `agents/`** (`HANDOFF.md`, `PRIORITY.md`, `CHANGELOG.md`, …) | Session / priority / history | **Agents** (user may edit; not intended workflow) |
| **`agents/design.md`** | Guiding-light design | **Agents** (after design meetings); optional until then |
| **`agents/plans/`**, **`plans/archived/`** | Plans + completed/abandoned archives | Agents + project |
| **`agents/design/`** | CHANGELOG + optional topic detail | Agents |
| **`agents/ideas/`** | Parked ideas | Agents + project |
| **`agents/blockers/`**, **`archive/`** | Human blockers; other ship summaries | Project (hand) for blockers |
| **`agents/installed/*`** | Portable guideline bodies from shellrc **agents-catalog** | **Only** `agents install` / `agents update` — **never** hand-edit |
| **`agents/<same-rel-as-installed>`** | **Extension** (default) — amends installed; **wins on conflict** | Prefer this for project deltas. Fold portable improvements into the catalog. |
| **`agents/<stem>.extend.md`** | Explicit extension (same rules) | Do **not** also keep same-name or `*.override.md` for that id |
| **`agents/<stem>.override.md`** | **Override** — replaces installed for that id | Rare durable fork only. Prefer extension or a catalog fix. |

Exactly **one** of the three layer forms may exist per installed file.
`agents update` **errors** if they are mixed.

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
