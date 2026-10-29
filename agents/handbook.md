# Handbook

When to use: Every agent reads this file once, from the line in
`AGENTS.md`. It is how the handbook works. It is not product design.

**Owner:** human. Apply edits only with permission in the current
message.

The handbook is the `agents/` directory. It is the rules for agents
working on this project. Product behavior lives in the guide, not
in this file.

## What is in force

`AGENTS.md` is injected on every turn. It holds the security kernel.
This file is the rest of what every agent needs.

`agents/.quarantine/` is not in force. A listing hides it.
Do not follow a file there.
There is no `agents.py`. `AGENTS.md` is the project's kernel, not a
generated index. `agent-handbook update` refreshes `agents/installed/`
from the catalog. It does not rewrite `AGENTS.md` and it does not
restore `agents.py`. Do not hand-edit `agents/installed/`.

The procedure is this file, [`roles/`](roles/),
[`plans/README.md`](plans/README.md), and
[`versions.md`](versions.md). There is no `general.md`.

## Finding a rule

Do not keep a second index of when to open each file. The old
index drifted, and it was injected on every turn.

When this file does not state the rule, search `agents/` for lines
that start with `When to use:`. Skip `agents/.quarantine/`. Open the
file whose line matches the task. Do not search the old `read_when`
field. That field was copied into the retired index.

The orchestrator reads the whole architecture. Another agent opens
the part the task names.

## One home

A fact has one home. The guide is the product. A plan is the work.
The glossary names a word and points at the guide. Do not restate
the guide in a plan, a role file, or this file.

Do not paste another repo's plans, tapes, or bug stories into
these files as if they were this product.

Ownership is declared in the file, not by filename case. Filenames
are lowercase except names an external standard requires
(`README.md`, `AGENTS.md`).

Do not keep a second full copy of a catalog file under `agents/`.
For one id, use one project form, not a mix. The names are the
extension and override rows in [`glossary.md`](glossary.md).

Human-owned files change only when the current message gives
permission. Those files are the product README, `project.md`,
`architecture.md`, the files under `architecture/`, `acceptance.md`,
`documentation.md`, `testing.md`, `plog.md`, and this file.
`agents/installed/` is refreshed by `agent-handbook update`. Do not
hand-edit it. On conflict, this handbook wins over a catalog file.

## Asking

Ask in the chat when a fact blocks the work, and include the
context. Do not use the `ask_user_question` tool.

A chat answer is for this session. It is not a file. Write it
down only when it changes the guide or a product check and the
human says to, or when the task note would otherwise leave the
next agent guessing. Do not open a conflict row, an issues row,
or an architecture paragraph to store the conversation.

Do not re-ask or ignore a prior answer. Re-ask only when new
context changed the meaning.

## Plans and tasks

The shape is [`plans/README.md`](plans/README.md). Read it when
you create, file, or prioritize a plan or a task. Copy
[`plans/_template/`](plans/_template/) when you create a plan.

[`priority.md`](priority.md) lists which plans come next. A plan's
own `priority.md` lists that plan's tasks. A plan has a rank.
The numbers are [`plans/README.md`](plans/README.md). A move
from one handbook version group to the next is
[`versions.md`](versions.md).

## Your role

You start with no role. Do the task in the user message. You are
not the orchestrator because you are the one speaking. Do not read
the work queue, and do not hand the task to another agent, unless
this conversation assigns the orchestrator role.

A role is assigned only in one of these ways:

1. The user says "Orchestrate this task" or "Orchestrate the
   prioritized work", or runs `/orchestrate`. Read
   [`roles/orchestrator.md`](roles/orchestrator.md) and follow it.
1. Your prompt says you are a delegate. Read
   [`roles/delegate.md`](roles/delegate.md) and follow it.
1. Your prompt names `developer`, `code reviewer`, `architect`,
   or `maid`. Read that role file as well.

Role files live in [`roles/`](roles/). The prompt that assigns the
role is what makes it true. A file cannot assign a role to the
agent who merely opened it.
