# Control names

**Rank:** 4

**Stage:** names

## Goal

The pages a person reads, and the extension's opening
sentence, name the run controls the way the runtime part
does. Those controls are Start, Pause, Clear All, Apply,
and Close. Start reads Restart after the step has been
started, until Clear All. Clear All returns a surround to
the wait. The pages do not offer Cancel or Change surround.

## Guide

- [`../../architecture/runtime.md`](../../architecture/runtime.md)
- [`../../architecture/preview.md`](../../architecture/preview.md)

## Checks

- README, the extension doc, the surround user page, and
  the extension's opening sentence do not tell the person
  to use Cancel or Change surround.
- Where a sentence named those controls, it uses the
  runtime names. The surround page says Start reads
  Restart after that step has been started, until Clear
  All, and Clear All is the return to the wait. The other
  three stay one mention of Start, Pause, Clear All,
  Apply, and Close. They do not become a second window.
- Island-hop stays. Conquer is not invented.
- The product does not change. The dialog and its tests
  stay as they are.
- This plan does not start until surround-doc's
  [join-label](../surround-doc/tasks/active/join-label/task.md)
  and
  [spinner-labels](../surround-doc/tasks/active/spinner-labels/task.md)
  are done. join-label owns the join-gap sentences in
  `docs/user/surround.md`. spinner-labels owns the
  spinner-label sentences in `docs/inkscape-extension.md`.
  The tasks in this plan stay ready.
