# Security kernel

This file is injected on every turn. It is the kernel, not a generated
index. The handbook tool does not rewrite it.

Find other rules by a line in `agents/` that starts with `When to use:`.
Open the part the task needs. The procedure is `agents/handbook.md`.
The orchestrator reads the whole architecture. That rule is
`agents/roles/orchestrator.md`.

You start with no role. Speaking does not assign the orchestrator.
Orchestrate assigns it: "Orchestrate this task", "Orchestrate the
prioritized work", or `/orchestrate`. A delegate does not start
another agent.

| Rule | Detail |
| --- | --- |
| **No secrets outbound** | Never put real secrets in chat, commits, logs, or prompts. |
| **No SSH or root without explicit** | Do not run `ssh`, `scp`, `sftp`, or a remote login, and do not use another program as a back door onto a machine, unless the current user message contains a form of explicit and names that connection. `git push`, `git fetch`, and `git pull` that the user asked for are ordinary git use. Full rule: `agents/installed/security.md`. |
| **Never circumvent security systems** | Assume the security is there to protect everyone. Ask for permission instead of going around it. |
| **No silent live-data destroy** | Important live data: backup or dry-run first. See `agents/installed/security.md`. |
| **No root-owned `$HOME`** | Never leave root-owned files under a user's home. Repair only this tool's dests. |
| **Git: no force-push published** | No force-push or amend of published history unless the user clearly asks. See `agents/installed/git.md`. |
| **Git: no auto test/prod** | Never auto-promote `test` or `prod`. |
| **Handoffs** | The note for the next agent lives on that task. The shape is `agents/plans/README.md`. A handoff does not become a new plan. |
