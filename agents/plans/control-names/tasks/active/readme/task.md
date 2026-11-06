# Readme

**Status:** ready

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

The developer writes what changed, why, and how it was checked.
The reviewer then writes the summary, the context worth keeping,
and the result.
