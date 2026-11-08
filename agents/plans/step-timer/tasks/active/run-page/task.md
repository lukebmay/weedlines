# Run page

**Status:** in-progress

## Goal

`docs/user/surround.md` matches the runtime part on how
long the started step has been working.

## Do

Edit only `docs/user/surround.md`. That is the user
page that mentions the run.

control-names surround-page also edits this file and
owns the control names. Leave the sentences it renames.
Do not write Start Algorithm or Change surround in the
new stretch. Do not rename the old ones.

In the Start section, in the order a person does the
work, say that the window shows how long that started
step has been working, with that step's status. Pause
holds the time. The time stays when the step is done.
Restart starts that time from zero. Clear All discards
it with the lines. Before the step is started, there
is no time.

One short stretch is enough. Do not add a procedure
for frame, grid, or island-hop. Do not give Conquer a
time. Do not name the two border labels. Do not invent
a cavern measure. Do not say the library owns the
clock. Do not edit the root `README.md`,
`docs/inkscape-extension.md`,
`docs/user/piece-border.md`,
`docs/user/correction-arrows.md`, or any code.

## Checks

- `docs/user/surround.md` is the only changed file.
- The new stretch shows the working time with that
  step's status, holds it on Pause, keeps it when the
  step is done, starts it from zero on Restart, and
  discards it on Clear All.
- A step not started has no time. Conquer has none.
- The new stretch does not say the library times the
  step, and it does not name a border label or a
  cavern measure.
- The new stretch does not say Start Algorithm or
  Change surround.

## Note

The Start section of `docs/user/surround.md` now follows the
run. Before the step is started, the window shows no time.
After **Start Algorithm**, it shows how long that started
step has been working, with that step's status. **Pause**
holds the time, and **Resume** continues that run so the
step can finish. The time stays when the step is done.
**Restart** starts that time from zero. **Clear All**
discards it with the lines. Those two come after the older
steps that still need the lines and an unlocked color
field. The Start Algorithm and Change surround sentences
are unchanged. Conquer is not given a time. The new lines
do not name a border label, a cavern measure, or the
library.

Why: the page did not say how long the started step had
been working. The runtime part says the window shows that
time with the step's status, holds it on Pause, keeps it
when the step is done, starts it from zero on Restart, and
discards it on Clear All. A step not started has no time.

Checked by reading the added lines against the step-time
sentences in `agents/architecture/runtime.md`. `git diff --
docs/user/surround.md` is only those lines. They do not say
Start Algorithm, Change surround, library, cavern, or
Conquer, and they do not name a border label. No other file
was edited for this task. Status left in-progress.

The reviewer then writes the summary, the context worth keeping,
and the result.
