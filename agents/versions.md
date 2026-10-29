# Versions

When to use: Installing a handbook, moving a project off an older
handbook, or deciding which migration to run.

**Owner:** agent. The groups and the steps below are the migration
record. A new group is a new row. Do not invent a migration that
this file does not list.

The version is the tool version. A project records it as
`tool_version` in `agents/installed/.meta.toml`. An older tree may
only have `# agents-tool-version:` in root `agents.py`.

## Groups

A group is a half-open range of tool versions that share one
handbook shape. The range is versions greater than or equal to the
first version, and less than the next group's first version.

| Group | Tool versions | Shape |
| --- | --- | --- |
| `agents` | >= 0.1.4 and < 0.7.0 | `agents` composes `AGENTS.md`. |
| `agent-handbook` | >= 0.7.0 | `agent-handbook`. No composer. |

In the `agents` group, root `agents.py` composes `AGENTS.md`.
In the `agent-handbook` group, `AGENTS.md` is the hand-owned
kernel and the procedure is `agents/handbook.md`.

`agent-handbook` has no upper bound yet. It is the latest group.
When the next group starts, set this row's upper bound to that
group's first version and add the next row, with the migration
that crosses the new boundary. The first version of `agents` is
0.1.4. The first version of `agent-handbook` is 0.7.0.

The target group is the group of the tool being installed. Today
that is `agent-handbook`.

## Crossing a boundary

Read the project's tool version and find its group. If that group
is the target group, stop. No migration is due.

If the project is in an earlier group, run one migration at a
time. Finish the boundary from the project's group to the next
group, including that boundary's triage plan, before the next
boundary. Do not skip a group. The only boundary today is
`agents` to `agent-handbook`.

A project with no version stamp is in the `agents` group when
root `agents.py` composes `AGENTS.md`. It is in the
`agent-handbook` group when `agents/handbook.md` and
`agents/roles/` exist and there is no composer.

## From agents to agent-handbook

This is the migration for versions >= 0.1.4 and < 0.7.0, into
>= 0.7.0. The plan it files is
`plans/complete-v0.1.4-v0.7.0-migration/`.

Skip a step that is already done. Do not run step 1 when
`agents/handbook.md` is already the live handbook.

### 1. Quarantine the old handbook

Create `agents/.quarantine/` if it is missing. Move every other
entry in `agents/` into it. Move root `AGENTS.md` into it. When
root `agents.py` is the composer that rewrites `AGENTS.md`, move
that file too. Leave `agents.py` in place when it is already the
retired stub that points at `agent-handbook`.

Do not move `.quarantine` into itself. After this step, `agents/`
holds `.quarantine/` and nothing else.

The quarantined files are not in force. Read one only when a
later step says to.

`agents/.quarantine/` is only this migration's holding area.
The tool's own conflict copies live in
`agents/.migrate-quarantine/`. Do not use that directory for
this step. `agent-handbook init` does not read
`agents/.quarantine/` and does not move files out of it. Do
not run `agent-handbook migrate` instead of these steps. That
command moves a catalog file that is still at `agents/<name>`
into `agents/installed/`.

### 2. Install the current handbook

Run `agent-handbook init` in the project. That seeds the handbook
and the core set. It does not overwrite a file that is already
there, and it does not write a composer.

Then install the languages and kits this project still needs.
Look at `agents/.quarantine/installed/`, including
`installed/languages/`, and at the quarantined project file for
the stack. Install a language or kit the project still uses
(`agent-handbook install`, or `agent-handbook kits install`).
Skip one the project no longer uses. Add one the project needs
now that the old tree did not have. Do not hand-edit
`agents/installed/`.

### 3. Carry the project facts

Read the quarantine and carry facts the new tree does not
already state. Copy a fact that still fits. Translate a fact
when the new files use a different shape. Leave process rules
the new handbook already states in quarantine. That includes a
generated index, `general.md`, and the composer.

These files may be filled from the quarantined copies. This
step is the permission to write them for this migration:

- What the product is, into `project.md`. Do not add a product
  claim the old file did not make.
- The guide, into `architecture.md`, and into `architecture/`
  when the old guide was one file per part or should become
  that. Do not invent a new design.
- Words, product checks, conflicts, and issues, into the files
  that already own them.

Plans and tasks:

- A directory that already matches [`plans/README.md`](plans/README.md)
  is copied, then checked against that shape.
- A flat plan file is translated into `plans/<name>/`. This
  step is the instruction to translate. The architect's stop
  on a flat file does not block it.
- An old `agents/tasks/` entry becomes a task under the plan it
  belongs to. When it was a whole piece of work, it becomes a
  plan.
- Finished work stays out of the live queue. Copy it under
  `plans/.archived/` only when a later agent would need it.
  Step 4 decides what is live.

### 4. File the triage plan

Create `plans/complete-v0.1.4-v0.7.0-migration/`. The name uses
the first version of the source group and the first version of
the target group. The plan is rank 5. The human asked for this
migration, and the old queue is not trustworthy until the
triage has ranked it. Ranks for every other plan are
[`plans/README.md`](plans/README.md).

The plan scans every plan now under `plans/`. For each one it
decides:

- It conflicts with another plan or with the guide. Name the
  conflict in [`conflicts.md`](conflicts.md). Do not implement
  either side until the human picks. The two lists in that
  file are the rule.
- It is old and irrelevant. Say why, and archive it.
- It overlaps another plan and the two are one piece of work.
  Combine them.
- A task is no longer relevant. Human waits from the old tree
  often are. Archive those tasks. Do not keep a wait an agent
  can do, and do not keep a wait for a product the guide no
  longer has.
- It can be closed. The work is done, or the guide no longer
  asks for it. Archive it.

Then rank each remaining plan and write
[`priority.md`](priority.md) in rank order. Rank 5, 2, or
1 still needs the human's word, except this triage plan, which
this step ranks 5. The carried plans are 3 or 4 unless the
human has already named another rank.

This plan is rank 5, so the rank rule applies to it. Before it
starts the rest of its work, it reads the carried plans for a
task that has to finish first so the triage can be done
correctly and efficiently. It names that task and does it
first. A rank 5 plan it creates later gets the same check.
