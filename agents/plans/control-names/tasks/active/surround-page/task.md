# Surround page

**Status:** ready

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

The developer writes what changed, why, and how it was checked.
The reviewer then writes the summary, the context worth keeping,
and the result.
