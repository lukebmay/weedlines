---
title: Comments
read_when: Adding or editing source comments
order: 50
---

# Comments

## Style (strict)

Keep comments **short and non-specific**.

- Prefer one short line or end-of-line
- Explain *why* only when non-obvious
- **Never** restate *what* the next lines clearly do
- **Never** embed volatile detail (history, review chat, long purpose essays)

Good: `# Grok` · `# Update check (quiet on no-op)`  
Bad: long banners, “expensive: …” essays

Design/history → `agents/design.md` / `agents/design/CHANGELOG.md` / plans — not source novels.

## General

- Prefer EOL over blocks when both exist
- No emoji unless the file already uses them
- Stale comments are worse than none
- Prefer clear names over comments
- Tags: `TODO`, `FIXME`, `NOTE`
- Update or delete when code changes

## Audience

Production comments for other developers: structure, non-obvious logic, external constraints. No session chat addresses.
