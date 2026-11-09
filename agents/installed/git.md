---
title: Git
order: 30
---

# Git

When to use: Before any commit, push, branch, merge, rebase, or release-ladder work.

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
| No force-push published | No force-push or amend of published history unless the user clearly asks |

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

## Commit and push

Commit when a task is complete. The reviewer commits if they approve. If they approve only with changes, the developer makes those changes and then commits. If no one is reviewing, the developer commits when the task is complete. Only one of them commits that task. Do not push until the work is functional and usable. That wait is not a full acceptance run. Branches are not required.

## Merge side branch → default (when used)

Gates: the change's own checks passed · default merged into the
feature first · tests for that change are green · no serious doubt ·
no queue interference. Then merge. Push follows the commit and push
rule above.
