# Surround page

**Status:** done

## Goal

`docs/user/surround.md` names Start and Clear All. It does
not tell the person to choose Start Algorithm or Change
surround.

## Do

Edit only `docs/user/surround.md`.

Every **Start Algorithm** becomes **Start**. That includes
the ones split across a line break. After that step has
been started, the page says the control reads **Restart**
until **Clear All**. One clause on the start step is
enough. Do not add a second procedure.

The step that says choose **Change surround**, then the
lines clear, the numbers stay, and nothing is drawn until
the next start, names **Clear All**. That is the return to
the wait. It is not Restart. Restart runs the step again.
Do not turn that step into Restart, and do not leave a
step that tells the person to choose Change surround. The
heading may stay. It is not a button.

Leave the mode-change steps as they are, apart from the
control name. Leave the join-gap sentences as they are.
surround-doc join-label owns those.

Do not invent conquer. Do not add or remove island-hop.
Do not name the library cancel exception. Do not edit the
window, product code, tests, or any other file.

## Checks

- The page does not say "Start Algorithm".
- It does not tell the person to choose "Change surround".
- The start control is **Start**. After that step has been
  started, the page says it reads **Restart** until
  **Clear All**.
- The step that cleared the lines and waited names
  **Clear All**.
- The join-gap sentences are unchanged by this task.
- `docs/user/surround.md` is the only changed file.

## Note

`docs/user/surround.md` names **Start** where it named
**Start Algorithm**, including the two that were split
across a line. The step that chooses **Start** has one
clause: after that step has been started, the control
reads **Restart** until **Clear All**. The step that
cleared the lines and waited names **Clear All**. It does
not say Change surround, and it is not Restart. The
heading stays. The time sentences, the join-gap
sentences, and the other mode-change steps are unchanged.
Conquer is not described. Island-hop is not added or
removed.

Why: the page told the person to choose Start Algorithm
and Change surround. The runtime names are Start, which
reads Restart after that step has been started until
Clear All, and Clear All for the return to the wait.
Restart runs the step again.

Checked by reading the page against the run controls in
`agents/architecture/runtime.md`. A search of the page
finds no "Start Algorithm" and no "Change surround".
`git diff -- docs/user/surround.md` is only those renames
and that one clause. The join-gap lines and the time
lines are not in that diff. No other product file was
edited. Status left `in-progress`.

Summary: No defects. The page names **Start** where it
named **Start Algorithm**, including the two split across
a line. One clause on the Choose **Start** step says the
control reads **Restart** until **Clear All**. The step
that clears the lines and waits names **Clear All**, not
Restart. The heading stays. It does not tell the person
to choose Change surround. The step-time boxes and the
join-gap sentences are otherwise unchanged. Conquer is
not added. Island-hop is not added or removed.

Context worth keeping: `git diff -- docs/user/surround.md`
is only those renames and that one clause. The names
match the run controls in `agents/architecture/runtime.md`.
Start reads Restart after that step has been started,
until Clear All. Clear All is the return to the wait.
The heading `## Change the surround` is not a button.
Other dirty files are other work and are not this change.
There is no automated test. The check was reading the
page and that diff. The pass is `cr-01.md`.

Result: No defects remain. The named checks passed.
There is no automated test.
