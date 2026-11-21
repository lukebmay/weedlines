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

A source file owns one responsibility. The ideal size is
under 1200 lines. Count lines a person can read. Do not
pack a line to come in under the count.

Look for a logical split before the count. Split on a
responsibility that already has a name. A window, a widget
that is not trivial, an algorithm, or one stage of that
algorithm. A trivial piece stays with its neighbor. Do not
split a small file into several files unless this code
already splits that same kind of piece that way. A 20-line
file stays one file.

A program that is a single source file stays one file
until it passes 5000 lines. A script that is the whole
program is the same. Do not open a file-size plan for
it before then.

When a file is over its count, or a reasonable split is
already clear, note the file and finish the current work.
The split is a later file-size plan. Do not start it
inside the current task. The plan breaks the file into
coherent pieces, or it says why the file should stay
large. The user hears that reason before the file is
left large.

When the user leaves the file large, record it in the
directory index. The entry names the file, the line count
it may reach, one sentence why, and the next count. The
usual next counts are 1500, then 1800, 2000, and 2200,
then steps of about 200. Use the next step above the
file's present size. A one-file program records the next
count the same way after 5000. The usual next counts
there are 6000, then 7000, then 8000. Reaching that
count starts the same note and a new file-size plan.
A directory that
has no index yet gets one for this entry.

Write code an average developer can read and change. Prefer the
direct structure. Keep the common path cheap to run. A highly
complicated or specialized algorithm may be dense when density is
what makes it correct. It may also be split into files or stages
when each part already has a name. Do not make it dense only
because this sentence allows it. The rest of the architecture
stays easy to follow. Name a long or dense algorithm in the
directory index.

A generated file or one table may be longer. Name that
exception in the directory index. Do not use it for a
module that mixes responsibilities.

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

Human-owned files are the product README, `project.md`,
`acceptance.md`, `architecture.md`, and the files under
`architecture/`. When they may change is
[Changing the guide](plans/README.md#changing-the-guide).
`agents/installed/` is refreshed by `agent-handbook update`. Do not
hand-edit it.

## The guide

The architecture and the human-owned files are a guide. They
can be wrong. A sentence may say the product works this way
for now.

An agent who sees a broken sentence says so. Push harder
while designing a new feature. Push less while implementing
a plan whose design is already accepted. Still say so when
the sentence is wrong or the finished product would be a bad
one.

The end is a useful product. Matching a bad design exactly is
not the end.

How the guide changes is
[Changing the guide](plans/README.md#changing-the-guide).
Opening a plan does not write the guide.

A part file that still says the human owns it follows
[Changing the guide](plans/README.md#changing-the-guide).

## Asking

Ask in the chat when a fact blocks the work, and include the
context. Do not use the `ask_user_question` tool. Stop. Do not
edit, commit, or delegate until the human answers in this chat.

A chat answer is for this session. It is not a file. Write it
down only when
[Changing the guide](plans/README.md#changing-the-guide)
says the guide or a product check may change, or when the task
note would otherwise leave the next agent guessing. Do not open
a conflict row, an issues row, or an architecture paragraph to
store the conversation.

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

## Handbook updates

Updating the agent handbook in a repo, or rolling the
catalog out to repos that already use it.

The catalog version is `catalog_version` in
`agents/installed/.meta.toml`. Changes since a version
are `agent-handbook changelog <version>`. The file is
`agent-handbook-catalog/changelog.md`. Headings are
`## <version>`, newest first. A newer entry replaces an
older one when they describe the same rule. Skip the
older entry. Versions before 0.9.15 have no entry.

A tree is on agent-handbook when `agents/handbook.md`
and `agents/roles/` exist, and root `agents.py` is
absent or is the retired stub that does not compose
`AGENTS.md`. Leave a tree whose `agents.py` composes
`AGENTS.md`. Do not `init`, `migrate`, or
`migrate-layout` that tree.

Look under `~/dev` and `~/Desktop`. Nested handbooks
that share a git repo are one update. A nested
directory with its own `.git` is its own update. Do
not commit the parent gitlink when that nested HEAD
moves. Skip `agents/.quarantine/`.

Record the repo's catalog version, then run
`agent-handbook update` with no `--all` and no
`--force`. The command refreshes `agents/installed/`
and root `AGENTS.md`. It does not copy
`agent-handbook-catalog/handbook/` into a project
that already has those files. Carry the seed changes
since the recorded version:

- Insert a missing section into `agents/handbook.md`.
  Keep a sentence the project added.
- Leave a project `architecture.md` that is no longer
  the blank seed. Apply the seed change only when
  that file is still the seed.
- Do the same for the other handbook seeds the
  command does not copy. Leave a file the project
  has rewritten.

Do not hand-edit `agents/installed/` or root
`AGENTS.md`. Do not edit the catalog during a
rollout. If update moves a file out of
`agents/installed/`, name that path.

After the update, create `agents/plans/handbook-update/`
or bring that plan up to date if it exists. The plan
names the catalog version from before the update and
the version now installed. It tells agents to bring
the code in line with `agent-handbook changelog`
for that range. It does not make those product edits.
Each correction is a plan named `handbook-<topic>`.
Related corrections share one plan.
`handbook-update` lists them.

The same plan reads the plans already in the repo.
A handbook may be updated again before that work is
finished, so check on every update. A plan whose
instructions disagree with the installed handbook is
rewritten to match, or dropped.

Plans opened before catalog 0.9.18 may not use the
`handbook-` prefix. The first `handbook-update` in a
repo says so. Find those plans by what they change,
not only by the prefix. After that repo has finished
the handbook plans opened for 0.9.18, every later
handbook plan uses the prefix.

Stage only the handbook paths this update changed,
including `agents/plans/handbook-update/` and any
handbook plan this update rewrote. Leave every other
dirty path unstaged.

Commit on `master` or `main`. Fetch first. Push when
that branch has an origin and was even with it before
this commit, so the push publishes only this update.
If the branch was already ahead, commit and do not
push, and report the ahead count. Push anyway only
when the current message says to publish that repo.
No origin means commit only. If fetch fails, still
update and commit, and do not push. Do not
force-push. Do not push `test` or `prod`.

When the change is to the catalog itself, a `files/`
row needs a version bump and a `sha256` of that file.
`agent-handbook update` stops when the hash does not
match. Handbook seeds under
`agent-handbook-catalog/handbook/` are not `[[files]]`
rows. A seed change bumps `catalog_version` once.
The same change adds a changelog entry headed by
that version.

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
