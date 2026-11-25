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

Promote a check into `acceptance.md` only when
[Changing the guide](#changing-the-guide) says that file
may change. The plan does not edit that file on its own
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

- `_bugs` holds bug reports and fixes. A reported bug is enough
  to create `_bugs`. The first step verifies it. An unconfirmed
  report is closed. The first one creates that perpetual plan.
  The plan does not replace the issues row. An issues row still
  records the bug ([`../issues.md`](../issues.md)).
- `_inbox` holds small work that was asked for and does not need
  its own plan. A minor change asked in chat is a task here.
  Do not create `_inbox` until a message asks.

Verified debt is a normal plan. It is not a task under `_bugs`
or `_inbox`.

## Archive

When a plan is done, the orchestrator removes it from the
project queue and moves the directory to
`plans/.archived/<name>/` in that same turn. A done plan
that is still listed is the same move. A perpetual plan,
a name that starts with `_`, stays. A normal listing
hides that directory. Do not open it to choose work.

## Templates

Copy [`_template/`](_template/) when you create a plan. It holds
`plan.md`, `priority.md`, `stages/stage.md`, and
`tasks/active/task/task.md`. Rename the copies. Do not file
`_template` on a queue. A directory whose name starts with `_`
stays open, and this one is the pattern, not a plan.

## Stages

Stages are optional. `plans/<name>/stages/<stage>.md` is a
note for one part of the plan. `plan.md` names the current stage
with `Stage: <stage>` only when `stages/<stage>.md` exists. Omit
that line when the file does not exist.

The architect writes tasks from the current stage only. A later
stage may gain a note when the product shape changes. It
does not gain tasks yet.

## Changing the guide

A change the human has not accepted asks first. Lay out the current rule, what is wrong or bad about it, and the new rule. Wait for the answer. Do not edit the guide yet. A finding written into the plan is not permission while that ask is still waiting.

Wording that the current behavior is wrong means the architecture of that feature is changing. That includes "we have been going about this wrong" and "we have to change this behavior."

Skip that ask when the human asked for the plan that contains the change, or when the human, while the plan is being created, says to go ahead and update the guide.

A plan that changes what a human-owned file says is written into that file in the same turn the plan is created. The human has accepted that change by asking for the plan, or by answering while the plan was being created. Do not leave the old sentence standing as the only text an agent will find.

Write two blocks next to each other, in the file that already owns the fact. Do not open a second home for it.

The first block is the accepted decision. Its first line is `Not yet implemented.` and the link to the plan. The sentences under that line are the rule the plan will implement. Write them so a later planning session can design against them without opening the plan. Name who does the thing, what they do, and what the person sees.

The second block is the language that plan replaces. Its first line is `Deprecated until that plan ships.` The sentences under that line are what the product still does. They are not a diary, and they are not a list of ideas that were rejected. A later planning session reads this block to see the current behavior while the plan is open.

An agent who is writing a new plan reads both blocks. An agent who is implementing this plan implements the accepted block. That agent does not implement the deprecated block. An agent who is implementing a different plan treats the deprecated block as what the product does today, and does not treat the accepted block as if it had already shipped.

When the plan changes before it is finished, update the accepted block in that same turn so it matches what the plan will now implement. Leave the deprecated block in place while that old behavior is still what the product does. If the plan change means the product no longer does that old behavior, replace the deprecated block with the behavior the product does now.

When the plan is finished, delete the deprecated block. Delete the `Not yet implemented.` line and the plan link. The accepted sentences remain as ordinary sentences of the guide. Then read every human-owned file that plan changed, and compare each changed sentence to what shipped. If a sentence does not describe the shipped behavior, correct it in that same turn. The correction matches the ship. It is not a new question for the human, and it is not a story of the attempt.

A plan that does not change a human-owned rule does not write those files.

A bug row does not change the design. Code that only lags a rule the guide already states is a plan, and that plan does not rewrite the sentence.

Do not refuse the accepted rule because the deprecated block still states the old one. The deprecated block is what the product does until the plan ships. It is not permission to keep the old design.

A chat answer is the permission when there is no plan. Write that rule into the file that already owns the fact, in that same turn. There is no open plan, so there is no `Not yet implemented.` line and no deprecated block. The sentence is the current rule. Do not write the conversation, a tape, a session note, or a wish into the guide.

The reason on an accepted rule is one or two sentences. It is not a bug diary and not a list of what was rejected.

Human-owned files are the product README, `project.md`, `acceptance.md`, `architecture.md`, and the files under `architecture/`. The product rows of `glossary.md` follow this section when they state a product fact.

Prefer a clear sentence to a short one. The next agent must be able to tell what is accepted, what is still shipping, and what has shipped, without guessing from a label.

## The product

A plan completes the product named in the guide. A later
plan does not narrow a goal so that aim is dropped. A
check that passes while the person-visible result fails
is not done.

## Logs

A plan that cites a log names the tape id. The lines the
task needs are copied into the plan or the task. A later
deletion of the log does not remove that copy. The copy
is the evidence. It is not the whole tape.

## A disposable pass

A pass in a disposable environment does not close a miss
the person still sees. When the named checks passed and
an open issues row is still what the human sees on the
machine they are using, the task stays open. The note
says the disposable pass succeeded and the row is still
open.

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
The developer writes the note on `task.md` before returning:
what changed, why, and how it was checked. The developer does not
change the status and does not move the directory.

The code reviewer writes `cr-01.md`, `cr-02.md`, and so on, in
the task directory. After every pass, the reviewer updates
`task.md` with the summary, the context worth keeping, and the
result. The orchestrator does not read the `cr-` files. The
developer does not write them.

When the reviewer reports no defect and the named checks passed,
except the case in [A disposable pass](#a-disposable-pass), the
orchestrator sets `done`, moves the directory to
`tasks/inactive/`, and removes it from the plan's `priority.md`.

The orchestrator lists `tasks/active/` only. Two tasks run at
the same time only when they name different files. Tasks that
name the same file are serial.

## Empty or contradictory queue

When a directory plan that is not done has no task left in its
`priority.md`, the orchestrator delegates an architect. The
architect is a delegate.
The orchestrator does not do that survey in this conversation,
and does not start a second orchestrator.

When the list and the directories disagree, the orchestrator
delegates a maid first. The maid matches the files. She does not
choose the next product work. If product work is missing, she
names it and the orchestrator delegates an architect.

The maid also runs when the user asks, including over `plans/`
as a whole.
