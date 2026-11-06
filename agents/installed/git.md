---
title: Git
read_when: Before any commit, push, branch, merge, rebase, or release-ladder work
order: 30
---

# Git

Rule vocabulary: **FIRM** / **GUIDELINE** / **MAY**. The words are in the project's `agents/glossary.md`.

## Words

| Word | Means |
| --- | --- |
| **commit** | Local commit only |
| **push** | `git push` — only if working `origin` |
| **merge to default** | Side branch → `main`/`master` (when isolated) |
| **promote** | Human: default → `test` → `prod` |

## Release ladder

```text
work on master (usual)  →  master (dev)  →  test  →  prod
optional side branch only when isolated              ↑ human only
```

| Branch | Role | Who |
| --- | --- | --- |
| **master/main** | Dev integration; **default work branch** | Agents |
| **plan/* / task/*** | Exception isolation only | Agents; merge back when gated |
| **test** | Staging | **Human** |
| **prod** | Production; must lag | **Human only** |

Agents **never** auto-merge/push `test` or `prod` unless user **explicitly** asks to promote.

## Push / remotes (FIRM)

| Rule | Detail |
| --- | --- |
| No origin → no push | Skip push entirely; local commit only |
| Broken origin | Report once; keep local commits |
| No secret push | Never commit/push secrets |
| No force-push published | Unless user clearly asks |

## Branch strategy (FIRM default)

**Work on master/main unless otherwise specified.**

| Rule | Detail |
| --- | --- |
| Master by default | Implement on default; do not auto-create `plan/*` |
| User/plan override | Honor “use a branch” / isolate flags |
| Pull before work | Ensure default is current when origin exists |
| Queue on default | `agents/{priority.md,plans,ideas,conflicts.md,conflicts-resolved.md,handbook.md}` always on default |

**Side branch only when:** user asks; high-risk multi-day break of daily-driver; parallel incompatible experiments; external PR/review.

If on a side branch: re-merge default regularly; refactor may defer product merges but still pull **`agents/`** from default. Merge back when complete + tested + no serious doubt.

## Commit / push discretion

| Situation | Commit? | Push? |
| --- | --- | --- |
| Successful wrap-up on default | Yes | Yes if origin |
| Solid slice of the work in progress | Yes | Same as a wrap-up. See Acceptance and push |
| Side branch wrap-up | Yes | Push side; merge→default when gated |
| User said don’t | No | No |
| Secrets in diff | No | No |
| Architecture miss / code review not approved | No wrap-up | No |

User veto always wins.

## Acceptance and push (FIRM)

Test the change you just made. Use the checks that change names.
Do not use a full acceptance run as that test.

Full acceptance is periodic. Run it after a large workload, about
once or twice a week, or once at the end of a stretch of active
development that is landing many changes. The product checks live
in `agents/acceptance.md`. That run is not a gate on every commit.

A push waits on acceptance only when the commit can change product
behavior. That is code. Handbook, documentation, and any other
change that cannot change product behavior do not wait. Push those
when the slice is solid.

A project git file may add a gate for code. It may not hold a
handbook change, a documentation change, or another change that
cannot change product behavior for an acceptance run.

## Merge side branch → default (when used)

Gates: the change's own checks passed · default merged into the
feature first · tests for that change are green · no serious doubt ·
no queue interference. Full acceptance follows the schedule above.
Then merge and push default if origin works.
