# Apply layer

**Status:** done

## Goal

Confirm the reported Apply sentence. If the page
already matches the runtime part, stop with no edit.
If it does not, that sentence matches the runtime
part.

## Do

A developer on the extension doc reported this.
Confirm it before changing any file.

The report: `docs/inkscape-extension.md` says
**Apply layer & Close** writes the Weedlines layer
into the document. The runtime part says Apply is
its own control. On Apply, the detached window
writes the result and does not edit the open
document. The person then runs `3 Reimport last
weedlines`. Close is a separate control.

Read `docs/inkscape-extension.md` and
`agents/architecture/runtime.md`. If the page
already says that, stop. Do not change files.

If the report is right, change only that
sentence. Do not edit the dialog-controls
sentence above it. control-names extension-doc
owns that sentence. If that task is still
active, stop after confirming and do not edit
yet. Do not edit the units section, the window,
or the solvers. Do not invent conquer.

## Checks

- If the report is wrong, no file changes, and
  the note says what the page says.
- If it is right and the edit is made, that
  sentence does not say Apply layer & Close
  writes the layer into the document. It matches
  the runtime Apply path.
- The dialog-controls sentence and the units
  section are unchanged by this task.
- There is no automated test for this sentence.
  Say so.

## Note

The report was right. The install step in
`docs/inkscape-extension.md` said **Apply layer & Close**
writes the Weedlines layer into the document. That sentence
now says **Apply** is its own control. On Apply, the detached
window writes the result and does not edit the open document.
The person then runs `3 Reimport last weedlines`. **Close**
is a separate control.

Why: Run in `agents/architecture/runtime.md` lists Apply and
Close as separate controls. On Apply, the detached window
writes the result and does not edit the open document. The
person then runs `3 Reimport last weedlines`.

Checked by reading that sentence against Run. `git diff --
docs/inkscape-extension.md` is that sentence only. The
dialog-controls sentence and the units section are not in
the diff. The sentence does not say Apply layer & Close
writes the layer into the document. Conquer is not
described. A search of `tests/` finds no reader of this
file. There is no automated test for this sentence. Status
left `in-progress`.

The same install step still names **Extensions → Inkcut →
Auto-gen Weedlines layer from selection…**. That is not
this sentence. `agents/plans/extension-doc-drift/plan.md`
already owns that drift. It was not edited here.

Summary: No defects. The sentence says Apply is its own
control. On Apply, the detached window writes the result
and does not edit the open document. The person then runs
`3 Reimport last weedlines`. Close is a separate control.
It does not say Apply layer & Close writes the layer into
the document.

Context worth keeping: `git diff -- docs/inkscape-extension.md`
is that sentence only, including against HEAD. The
dialog-controls sentence and the units section are not in
the diff. Conquer is not described. The install step still
names **Extensions → Inkcut → Auto-gen Weedlines layer from
selection…**. That path stays with
`agents/plans/extension-doc-drift/plan.md`. Do not treat it
as a defect here. No file under `tests/` reads this page.
The pass is `cr-01.md`.

Result: No defects remain. The named checks passed. There
is no automated test. The checks are reading the sentence
and the diff.
