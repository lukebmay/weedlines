---
title: Git
read_when: Before any commit, push, branch, merge, rebase, or release-ladder work
order: 30
---

# Git

Rule vocabulary: **FIRM** / **GUIDELINE** / **MAY** (see `general.md`).

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
| Queue on default | `agents/{PRIORITY,HANDOFF,plans,tasks,blockers,archive}` always on default |

**Side branch only when:** user asks; high-risk multi-day break of daily-driver; parallel incompatible experiments; external PR/review.

If on a side branch: re-merge default regularly; refactor may defer product merges but still pull **`agents/`** from default. Merge back when complete + tested + no serious doubt.

## Commit / push discretion

| Situation | Commit? | Push? |
| --- | --- | --- |
| Successful wrap-up on default | Yes | Yes if origin |
| Side branch wrap-up | Yes | Push side; merge→default when gated |
| User said don’t | No | No |
| Secrets in diff | No | No |
| DESIGN-FLAW / unfinished taskforce | No wrap-up | No |

User veto always wins.

## Merge side branch → default (when used)

Gates: acceptance met · default merged into feature first · tests green · no serious doubt · no queue interference. Then merge and push default if origin works.
