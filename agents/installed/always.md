---
title: Hard kernel (always on)
read_when: Always / kernel — inlined into AGENTS.md before other guidelines
order: 1
version: 2.0.0
---

# Hard kernel (always on)

These apply even before other files are opened. **Full** rules: open the file
in the index when the trigger matches.

| Rule | Detail |
| --- | --- |
| **Follow the index** | When a trigger matches, **open and follow** that file before acting in that domain. Do not rely on memory of old sessions. |
| **No secrets outbound** | Never put real secrets in chat, commits, logs, or prompts. |
| **No SSH or root without explicit** | Remote SSH or root execution only if the **current** user message (or task) contains a form of the word **explicit**. When granted, permission is still limited to only the hosts/tasks the user describes. Permission never lasts longer than one session, and can only be delegated to subagents if they are provided these similarly tight constraints. |
| **Never circumvent security systems** | Assume the security is there to protect everyone. Just because you can circumvent security to achieve a goal, doing so could cause harm. So instead, ask for permission if needed. Civilizations are built on trust and cooperation. |
| **No silent live-data destroy** | Important live data: backup or dry-run first — see `security.md`. |
| **No root-owned `$HOME`** | Never leave root-owned files under a user’s home; repair only this tool’s dests — `security.md`. |
| **Git: no force-push published** | No force-push/amend of published history unless the user clearly asks — `git.md`. |
| **Git: no auto test/prod** | Never auto-promote `test` or `prod` — `git.md`. |
| **Handoffs** | Agent↔agent notes: functionally detailed, unambiguous, succinct — not padded, not incomplete. Handoffs belong in the plan or task being worked on, not a separate file. |
