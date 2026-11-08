# Extension doc

**Status:** done

## Goal

`docs/inkscape-extension.md` stops saying the dialog opens
on Start Algorithm / Cancel.

## Do

Edit only `docs/inkscape-extension.md`.

The install step that says a custom dialog opens with
**Start Algorithm** / **Cancel…** names Start, Pause, Clear
All, Apply, and Close instead. Leave the rest of that
paragraph, including the log, the preview, and the
following Apply sentence. Do not rewrite the install
steps.

Do not edit the units section. surround-doc spinner-labels
owns those sentences. Do not edit the window or the
solvers. Do not invent conquer. Do not remove island-hop
if this file names it.

## Checks

- The file does not say "Start Algorithm" or offer Cancel
  as a control.
- That dialog sentence names Start, Pause, Clear All,
  Apply, and Close.
- The units section is unchanged by this task.
- `docs/inkscape-extension.md` is the only changed file.
- No product test reads this file.

## Note

The install step in `docs/inkscape-extension.md` named the dialog
**Start Algorithm** / **Cancel…**. That sentence now names
**Start**, **Pause**, **Clear All**, **Apply**, and **Close**.
The log, the live preview, and the following **Apply layer &
Close** sentence are unchanged. The units section is unchanged.
Island-hop stays. Conquer is not described.

Why: the runtime part names those five run controls. The page
was still offering Start Algorithm and Cancel.

Checked by reading the paragraph against Run in
`agents/architecture/runtime.md`. The file does not say
"Start Algorithm" and does not offer Cancel as a control.
The dialog sentence names Start, Pause, Clear All, Apply, and
Close. `git diff -- docs/inkscape-extension.md` is that
sentence only; the units section is not in the diff. A search
of `tests/` finds no reader of this file. Status left
`in-progress`.

Summary: No defects. The install step names Start, Pause,
Clear All, Apply, and Close. It does not say Start
Algorithm and does not offer Cancel. The log, the live
preview, and the following Apply layer & Close sentence
are unchanged. The units section is unchanged. Island-hop
stays. Conquer is not added.

Context worth keeping: `git diff -- docs/inkscape-extension.md`
is that control list only. Other dirty files belong to
other control-names tasks and are not this change. The
**Apply layer & Close** sentence was left on purpose. That
mismatch is already filed as
`agents/plans/_bugs/tasks/active/apply-layer/task.md`. Do
not treat it as a defect here. **Collar (island-hop)**
remains in the units section. The page does not describe
conquer. No file under `tests/` reads this page. The pass
is `cr-01.md`.

Result: No defects remain. The named checks passed. There
is no automated test. The checks are reading the page and
the diff.
