# Plans

When to use: Creating, filing, reading, or prioritizing a plan or a
task. A role file sends you here when the work is a plan.

**Owner:** agent, for the queue and the tasks. The guide stays the
product. Do not copy it into a plan or a task.

## Plan

`plans/<name>/plan.md` is the entry. Any agent who touches the plan
reads it. Keep it to the goal, the current stage, and pointers to
the guide and the checks. Failed attempts go in `notes.md` in that
same directory. Open `notes.md` only when the task says the attempt
matters.

When someone asks for a plan, write that directory in this repo.
Do not use Grok plan mode (`enter_plan_mode`, a session `plan.md`).
A session scratch file, or a copy under `/tmp`, is not the plan
unless the current message says so.

A flat plan file is the old shape. An architect or a maid who is
handed one stops. Do not invent `tasks/` beside it unless that
task says to translate it.

Promote a check into `acceptance.md` only when the current message
gives permission. The plan does not edit that file on its own
say-so.

`plans/<name>/priority.md` is the order of that plan's active
tasks. It is a list of paths. It is not a diary.

[`../priority.md`](../priority.md) is the queue of plans. It is not
the task list. A directory that file does not list is not the
queue. A "do not" there applies to the plan it names. The order
is [Rank](#rank).

A plan has no status line. Do not put `Status:` on `plan.md`.
It does have a rank line, `**Rank:** N`.

## Rank

Every plan has a rank. The queue lists higher ranks first.
Within one rank, the order in [`../priority.md`](../priority.md)
is the order of work. A plan with no rank line is 3 until a
ranking sets it.

| Rank | Name |
| --- | --- |
| 5 | top |
| 4 | high |
| 3 | medium |
| 2 | low |
| 1 | optional |

An agent who is asked to prioritize chooses 3 or 4.

Choose 2 or 1 only when the human specifically says that rank,
or specifically says low or optional.

Choose 5 when the human says that rank, or says top. Also
choose 5 when the human is telling you, in this chat, to fix
something or to plan a fix, and is not asking you to file that
work into the normal queue.

Before a rank 5 plan starts, read the other plans. If a task
already in one of them has to finish first so this plan can be
done correctly and efficiently, name that task on the rank 5
plan. Do that task first. The other plan keeps its rank. Do
not start the rank 5 plan until that task is done, or the
human says to go ahead without it.

A waiting plan stays under its rank. The notes say why. The
orchestrator skips it and takes the next plan. When the queue
is still one list, the next plan is the highest rank that is
not waiting. Within one rank, the list order stands.

## Perpetual plans

A directory whose name starts with `_` stays open. It is not
archived. `_bugs` and `_inbox` are part of the shape.

- `_bugs` holds bug reports and fixes. A verified bug is enough
  to create `_bugs`. The first one creates that perpetual plan.
  The plan does not replace the issues row. An issues row still
  records the bug ([`../issues.md`](../issues.md)).
- `_inbox` holds small work that was asked for and does not need
  its own plan. A minor change asked in chat is a task here.
  Do not create `_inbox` until a message asks.

Verified debt is a normal plan. It is not a task under `_bugs`
or `_inbox`.

## Archive

A plan that would confuse a later agent moves to
`plans/.archived/<name>/`. A normal listing hides that directory.
Do not open it unless the user says to. A perpetual plan does not
move there. The maid suggests the move. She does not make it.

## Templates

Copy [`_template/`](_template/) when you create a plan. It holds
`plan.md`, `priority.md`, `stages/stage.md`, and
`tasks/active/task/task.md`. Rename the copies. Do not file
`_template` on a queue. A directory whose name starts with `_`
stays open, and this one is the pattern, not a plan.

## Stages

Stages are optional. `plans/<name>/stages/<stage>.md` is a short
note for one part of the plan. `plan.md` names the current stage
with `Stage: <stage>` only when `stages/<stage>.md` exists. Omit
that line when the file does not exist.

The architect writes tasks from the current stage only. A later
stage may gain a short note when the product shape changes. It
does not gain tasks yet.

## Task

A task is work one session can finish.

`plans/<name>/tasks/<bucket>/<task>/task.md`

The bucket is `active`, `inactive`, or `.archived`. The status
line in `task.md` matches the bucket. When an agent lists work,
the directory wins. A line that disagrees is a maid report, not
a second bucket.

A task names its checks. It does not copy the guide.

### Active

- `ready` — ready for work
- `in-progress` — some work has been done
- `regression` — reopened because the finished work broke

### Inactive

- `waiting` — blocked. The task names the blocker. A human
  decision counts. A wait that names nothing is not a status.
  Do not call it a human wait when an agent can do the work.
  Do not clear a human wait unless the current message says
  that step is done.
- `parked` — do not continue. The plan changed, or something
  has to be looked into before the task is real again.
- `done` — finished and tested. Still useful as a reference.

### Archived

`tasks/.archived/` is hidden on purpose. Do not open it unless
the user says to.

- `dropped` — will not do. It sat parked, the plan changed, or
  it is too big or not worth doing.
- `archived` — it was `done`, and it is no longer useful as a
  reference.

## Who writes what

The orchestrator sets `in-progress` when it starts the developer.
The developer writes a short note on `task.md` before returning:
what changed, why, and how it was checked. The developer does not
change the status and does not move the directory.

The code reviewer writes `cr-01.md`, `cr-02.md`, and so on, in
the task directory. After every pass, the reviewer updates
`task.md` with the summary, the context worth keeping, and the
result. The orchestrator does not read the `cr-` files. The
developer does not write them.

When the reviewer reports no defect and the named checks passed,
the orchestrator sets `done`, moves the directory to
`tasks/inactive/`, and removes it from the plan's `priority.md`.

The orchestrator lists `tasks/active/` only. Two tasks run at
the same time only when they name different files. Tasks that
name the same file are serial.

## Empty or contradictory queue

When a directory plan has no task left in its `priority.md`, the
orchestrator delegates an architect. The architect is a delegate.
The orchestrator does not do that survey in this conversation,
and does not start a second orchestrator.

When the list and the directories disagree, the orchestrator
delegates a maid first. The maid matches the files. She does not
choose the next product work. If product work is missing, she
names it and the orchestrator delegates an architect.

The maid also runs when the user asks, including over `plans/`
as a whole.
