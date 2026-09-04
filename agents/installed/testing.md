---
title: Testing
read_when: Adding tests, changing test strategy, enabling optional features, checking Grok durable --leader mode, or reattaching headless Grok for the human
order: 70
---

# Testing

Rule vocabulary: **FIRM** / **GUIDELINE** / **MAY** (see `general.md`).

## Goal

Catch real bugs without making change expensive. Tests serve the product.

## Optional features in dev (FIRM)

When implementing/debugging an optional feature: **turn it on** in local/dev for that work. Record the enable command in task/handoff. Prefer tests that force the optional path explicitly.

## Pyramid (GUIDELINE)

| Layer | When | Cost |
| --- | --- | --- |
| Unit | Pure logic, parsers, validators | Cheap — be thorough once contract is clear |
| Integration | Critical paths + known gotchas | Few, high value |
| E2E / manual | Full UI when ROI is clear | Rarest |

Do not chase coverage numbers. Prefer one test that would have caught a real bug.

## Lifecycle

| Phase | Stance |
| --- | --- |
| Shape still moving | Sparse tests; unit only on stable pure helpers |
| Contract locked | Build unit suite; integration on critical paths |
| Bug found | Regression test when cheap and non-brittle |

## Do / don’t

**Do:** boundaries, invariants, critical paths once stable, focused regressions.  
**Don’t:** assert private call order, mirror implementation, freeze experimental APIs mid-design.

## Design is the test spec (FIRM)

Tests encode the **product contract** (design docs, user-visible behavior),
not the current implementation.

| Do | Do not |
| --- | --- |
| Change tests when **design** or a **user-visible bug** changes | Rewrite a test so today’s code goes green |
| Treat code vs test disagreement as **code wrong** until design is explicitly changed in the same effort | “Adapt the test to the helper we just wrote” |
| E2E / acceptance: **black box** — user gesture in, observable state out | E2E whose only assert is call-order, private spies, or internals |

Unit tests **may** pin a stable helper. That does not license E2E that
mirrors the call graph. If an E2E was authored by reading production
functions rather than the design, it is invalid — rewrite from the
contract.

Regressions that would have caught a real user bug beat twenty
implementation-mirrors.

## E2E story tree (FIRM when the project has an E2E harness)

Organize E2E as a **tree of stories**, not a flat bag of scripts.

| Node | Role |
| --- | --- |
| **Trunk** | Few coarse stories for the main user journeys. After a change, run the **lightest trunk** that covers the blast radius (catch an obvious break in that area). |
| **Branch** | Finer stories under a trunk. Run when the trunk fails, or when the change is in that subsystem. |
| **Leaf** | Edges and named regressions. Run when the branch fails, or on an RC. |

- Day-to-day: trunk (or one branch) — not the whole forest.
- Trunk **fail** → investigate **down that tree**. Do not weaken the trunk.
- **Release candidate:** run the **full tree**. A green trunk is not an RC
  bill of health.

Name stories in **user sequence** language (open, split, close, apply),
never helper names.

## In-progress features (GUIDELINE)

While a feature is **partially implemented**, its E2E stories **need not
pass**. Failures must be the **expected missing contract**, recorded on
the plan (which story, what still fails). Do not delete or weaken the
story to go green. Unrelated trunk failures are **not** “expected.”

## User-visible contract (FIRM for E2E)

E2E asserts what the user **can see or depend on in the current view**.
Work that is allowed to finish **off-screen** (background settle, hidden
surfaces, other spaces) is not a failure unless it later **shows**
wrong, blocks the visible path, or corrupts durable state the user will
meet. Do not fail a story because an invisible peer is still settling.

## Brittleness

Prefer observable outputs, stable fixtures, injected time/random, temp dirs. Avoid real clocks, important live data (see `security.md`).

## plog log-contract tests (GUIDELINE)

When the project uses **plog** / `plog-query` / an app log wrapper: bugs found
via hunts should prefer a small **log-contract** regression (stable JSONL
token + optional field + state oracle) when the harness can see the tape.
Anti-brittleness, regression discipline, and out-of-scope rules live in
catalog **`plog.md`** § Log-contract testing — do not snapshot full TRACE or
assert ANSI/pretty.

## CI (GUIDELINE)

Unit green on every change when CI exists. Critical integration should not be “never run.”

## Grok leader mode (FIRM for safety choices)

Agent tool subprocesses may run under a durable Grok **leader** (`grok --leader` /
shellrc `bin/grok` wrapper). Mid-flight work then survives TTY/window death; closing
the terminal is **not** a reliable “kill the agent” signal.

### Detect leader mode

Probe in order; first yes wins:

```bash
# 1) Preferred — Grok exports this for tools under a leader client
[[ -n "${GROK_LEADER_SOCKET:-}" ]]

# 2) Socket actually present (stronger than env alone)
[[ -n "${GROK_LEADER_SOCKET:-}" && -S "${GROK_LEADER_SOCKET}" ]]

# 3) Parent is the leader process (tools are often reparented under it)
ps -o args= -p "$PPID" 2>/dev/null | grep -q 'agent leader'
```

Optional status (human/debug, not required each turn):

```bash
grok --status   # shellrc wrapper: leader reachable + pid + socket
```

| Signal | Meaning |
| --- | --- |
| `GROK_LEADER_SOCKET` set | Running with a leader socket (durable path) |
| `GROK_AGENT=1` | Tool is inside a Grok agent turn — **not** leader-specific |
| Parent `agent leader` | Tool process is under the durable leader |

### Safe vs unsafe when leader is on

| Safe / preferred | Avoid or gate carefully |
| --- | --- |
| Long builds, tests, `sleep`, network I/O | Assuming “close the window kills this turn” |
| Writing markers/logs for later reattach | Destructive desk ops without user intent (`forge layout clean`) |
| `grok --list` / `--status` for recovery | Stopping the shared leader mid-session (`grok --stop`) unless asked |
| User-facing launches via `user-env` (see `scripting.md`) | Leaving monochrome agent env on GUI/layout commands |

When **not** in leader mode, treat the agent process as TTY-scoped: window death can
abort mid-work; prefer shorter critical sections and explicit checkpoints.

### Reattach for the human (FIRM after headless / detached work)

When agent work used **headless or detached** Grok (`grok --detach`, background
leader, headless `-p`, or tests that may **close** the terminal that launched
Grok), after that work is **complete**: open a **user-visible terminal** and
**reattach the head** so the operator can see results live. Do not leave them
with only a chat summary when a live leader/session still holds the work.

```bash
user-env grok                 # durable TUI attach (shellrc wrapper)
user-env grok --attach        # same intent
user-env grok -r <session-id> # known session
grok --list                   # discover session ids if needed
```

| Do | Don’t |
| --- | --- |
| Reattach after acceptance / wrap-up of headless work | Assume the human read the transcript only |
| Use `user-env` so the TUI is not monochrome (`scripting.md`) | Start a second unrelated session when reattach would show the same work |
| Prefer the existing leader/session | `grok --stop` just to “clean up” after a successful turn |

Skip only if the user said not to, or there was never a durable/headless session.
