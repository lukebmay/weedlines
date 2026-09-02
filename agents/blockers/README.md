# Human blockers

Work that **only a human** can do. Not every open question is a blocker.
**Real** human blockers only — not agent laziness.

## Hard vs soft

| Severity | Meaning |
| --- | --- |
| **hard** (default if omitted) | Required path stopped; plan `blocked`; taskforces skip |
| **soft** | Optional product/design/ops; does **not** stop the whole queue |

| Rule | Detail |
| --- | --- |
| Agents | Do **not** implement **hard** blockers. Soft: only if work is finalized and in scope. |
| Prep first | Agent installs/configs/stages anything it can so the human only does the human part. |
| Make it easy | Exact checklist, commands, paths, expected before/after. |
| Humans | Check boxes / mark `**Status:** done` or **parked** and move to `completed/` when finished. |
| CLI | `agents blockers` · `agents priorities` |
| Dates | Set **Created** on open; bump **Updated** on material edits. |

See catalog `general.md` (Human blockers) for what belongs here vs agent work.

Template:

```markdown
# B-short-id — Title

**Status:** open
**Severity:** hard | soft
**Owner:** human
**Kind:** design | permission | verify | credentials | physical | expensive-test | other
**Plan:** (none) | plan-id
**Unblocks:** agents/plans/some-plan.md
**Priority:** P0
**Created:** YYYY-MM-DD
**Updated:** YYYY-MM-DD

## Why this is human-only
…

## Agent prep already done
- [x] …

## What the human must do
- [ ] Exact step (command or UI path)

## Done when
…

## If human needs context
- Links / risks:
```
