---
title: Comments
order: 50
version: 2.3.3
---

# Comments

When to use: Adding or editing source comments.

## Style (strict)

Keep comments short and specific. Say the constraint the next reader would not see, including the invariant of a specialized algorithm. Do not narrate the steps.

- Prefer one short line or end-of-line
- Do not restate what the next lines already make obvious
- Do not embed a history, a review chat, or a long purpose essay

Good: `# Grok` · `# Update check (quiet on no-op)`  
Bad: long banners, “expensive: …” essays

Architecture and leftover names → `agents/architecture.md` /
`agents/conflicts.md` / plans — not source novels. Retired conflict
rows in `agents/conflicts-resolved.md` are not rules.

## General

- Prefer EOL over blocks when both exist
- No emoji unless the file already uses them
- Stale comments are worse than none
- Prefer clear names over comments
- Tags: `TODO`, `FIXME`, `NOTE`
- Update or delete when code changes

## Audience

Production comments for other developers: structure, non-obvious logic, external constraints. No session chat addresses.
