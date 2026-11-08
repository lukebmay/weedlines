# Readme

**Status:** done

## Goal

`README.md` stops calling the dialog Start / Cancel. The
abort a person reads is Clear All.

## Do

Edit only `README.md`.

The opening sentence says Start / Cancel. Name Start,
Pause, Clear All, Apply, and Close instead. Keep it one
sentence, with the live preview. Do not turn the paragraph
into a second window, and do not walk Restart there.

Under Pause / resume, **Pause** and **Resume** stay. The
sentence that says **Cancel** aborts, including while
paused, names **Clear All**. Leave the sample. Its
`cancel` argument is the hook, not a button. Do not name
the exception in the prose.

Do not remove island-hop. Do not invent conquer. Do not
edit the window, product code, tests, or any other file.

## Checks

- The opening does not say "Start / Cancel". It names
  Start, Pause, Clear All, Apply, and Close.
- The abort sentence names **Clear All**, including while
  paused. Pause and Resume stay.
- The sample still passes `cancel`. The prose does not
  name the exception.
- Island-hop remains in the algorithms list.
- `README.md` is the only changed file.

## Note

The opening sentence of `README.md` no longer says Start /
Cancel. It names Start, Pause, Clear All, Apply, and Close,
and it still has the live preview. It does not describe
Restart or a second window. Under Pause / resume, **Pause**
and **Resume** stay. **Clear All** aborts, including while
paused. The sample still passes `cancel`. The prose does
not name the library exception. Island-hop stays in the
algorithms list. Conquer is not described.

Why: the runtime names those five controls. Clear All is
the abort a person reads, including while paused. The
sample's `cancel` argument is the hook, not a button.

Checked by reading the two sentences against Run and
Progress in `agents/architecture/runtime.md`. `git diff --
README.md` is only those sentences. The file does not say
Start / Cancel. It does not name the library exception.
`island-hop` is still in the algorithms table and in the
install line. No other file was edited for this task.
Status left `in-progress`.

Summary: No defects. The opening names Start, Pause, Clear
All, Apply, and Close, and it still has the live preview.
It does not say Start / Cancel and it does not walk
Restart. Under Pause / resume, Pause and Resume stay, and
Clear All aborts, including while paused. The sample still
passes `cancel`. The prose does not name the library
exception. Island-hop remains. This change is only
`README.md`.

Context worth keeping: `git diff -- README.md` is those two
sentences. Other dirty files belong to other control-names
tasks. Do not treat them as this change. "Restart Inkscape"
on the install line is not the Restart control, and this
diff does not touch it. There is no automated test for
these sentences. No test reads `README.md`. The check is
reading the two sentences against Run and Progress in
`agents/architecture/runtime.md`. The pass is `cr-01.md`.
Status stays `in-progress`.

Result: No defects remain. The named checks passed. There
is no automated test for these sentences.
