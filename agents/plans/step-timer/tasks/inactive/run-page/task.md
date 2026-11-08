# Run page

**Status:** done

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

Summary: No defects. The Start section shows no time before
the step is started, then the working time with that step's
status. Pause holds it, and the time stays when the step is
done. Restart starts it from zero. Clear All discards it with
the lines. Conquer is not given a time. The new boxes do not
say Start Algorithm, Change surround, the library, a border
label, or a cavern measure. The older Start Algorithm and
Change surround sentences are still there.

Context worth keeping: Restart and Clear All stay after the
mode-change box. That box clears the lines, then returns to
Surround and Conquer and draws the surround again. Leaving
the mode does not discard the started step, so the time the
earlier boxes set up is still showing when Restart sets it
to zero. The pass is `cr-01.md`. `git diff --
docs/user/surround.md` is only those boxes. Do not treat
`extensions/inkscape/weedlines_dialog/run_controls.py`, or
the other dirty files, as this change. There is no automated
test. No test reads the page.

Result: No defects remain. The named checks passed. There
is no automated test.
