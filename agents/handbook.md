# Handbook

When to use: ALWAYS

The agent-handbook owns its files first. It may delegate control
or ownership of a file to a human or an agent.

The handbook is the `agents/` directory. It is the rules for agents
working on this project. Product behavior lives in the guide, not
in this file.

## What is in force

`AGENTS.md` is injected on every turn. It only tells the agent to
read `agents/installed/security.md`, `agents/installed/git.md`, and
`agents/handbook.md`. `agent-handbook init` and `agent-handbook
update` overwrite root `AGENTS.md` from the catalog seed. They do
not rewrite the other handbook files. Do not restore `agents.py`.
Do not hand-edit `agents/installed/`.

If `project.md` or `architecture.md` is still the blank template,
the orchestrator asks the human whether to proceed without them,
and does not delegate and does not guess. A delegate does not ask
the human. It returns the question in the summary and does not edit.

`agents/.quarantine/` is not in force. A listing hides it.
Do not follow a file there. There is no `agents.py`.

The procedure is this file, [`roles/`](roles/),
[`plans/README.md`](plans/README.md), and
[`versions.md`](versions.md). There is no `general.md`.

## Finding a rule

Do not keep a second index. Open every file whose `When to use:`
line is `ALWAYS`. Every other file has exactly one such line.
Search `agents/` for that line. Skip `agents/.quarantine/`. Open
the file whose sentence matches the task. Do not search
`read_when`.

The orchestrator reads only the relevant architecture files. Another
agent opens the parts the task needs. That rule is
[`roles/orchestrator.md`](roles/orchestrator.md).

## Source files

A source file owns one responsibility. 500 lines is the
usual ceiling. When a file past 1000 lines is noticed,
a separate plan is created to break that file apart on
a named responsibility. The task already in progress continues.
The split is not started inside it.

A file under 500 lines stays whole. Do not split it to
hit a count. From 500 to 1000, split only when the new
code is a separate responsibility.

Write code an average developer can read and change. Prefer the
direct structure. Keep the common path cheap to run. A highly
complicated or specialized algorithm may be dense when density is
what makes it correct. It may also be split into files or stages
when each part already has a name. Do not make it dense only
because this sentence allows it. The rest of the architecture
stays easy to follow. Name a long or dense algorithm in the
directory index.

Split on a responsibility that already has a name. A
window, a widget that is not trivial, an algorithm, or
one stage of that algorithm. A trivial piece stays with
its neighbor. A generated file or one table may be
longer. Name that exception in the directory index. Do
not use it for a module that mixes responsibilities.

Put new code in the file that already owns that work,
then stop. Do not shop for a finer split.

A directory with more than one source file has an index.
Each entry is the file name and one sentence for what
that file owns. Open the index, then the one file the
task needs. Leave the other files closed. The index is
a map. It does not copy the file.

This covers product code, tests, plans, and the
handbook. The sentence above that forbids a second
handbook index is about the old index that was injected
on every turn. A directory index of source files is this
section.

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
`architecture.md`, the files under `architecture/`, and
`acceptance.md`.
`agents/installed/` is refreshed by `agent-handbook update`. Do not
hand-edit it.

## Asking

Ask in the chat when a fact blocks the work, and include the
context. Do not use the `ask_user_question` tool. Stop. Do not
edit, commit, or delegate until the human answers in this chat.

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
