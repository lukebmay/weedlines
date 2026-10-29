# User surround

**Status:** done

## Goal

A person can follow the surround preview through approval
without a second guide in the root README.

## Do

- Add `docs/user/surround.md`. Write it for a person following
  along. The tone rules are `agents/installed/documentation.md`.
  Do not edit `docs/user/correction-arrows.md`.
- Cover the window opening on Surround and Conquer, the surround
  distance, the preview, Start Algorithm as approval, and Change
  surround. The behavior is Surround preview in
  `agents/architecture/preview.md` and Surround and Conquer in
  `agents/architecture/algorithms.md`. Do not copy those parts
  into the page.
- When the line under the preview names problems, say that no
  surround is shown and Start stays off, and point at the
  correction page. Do not repeat that page.
- Do not document conquer, a second surround, or a smoothing
  control. Do not edit the root `README.md` or any code.

## Checks

- The page is `docs/user/surround.md`. The root README is
  unchanged. `docs/user/correction-arrows.md` is unchanged.
- The steps follow the order a person does them. They name
  Surround distance, Start Algorithm, and Change surround.
- Start Algorithm is described as approval. The page says it
  does not write a result.
- The page does not describe conquer, a second surround, or a
  smoothing control.

## Note

Added `docs/user/surround.md`. A person opens the window on
Surround and Conquer, reads the line under the preview, sets
Surround distance, watches the preview, and uses Start Algorithm
as the approval. The page says that approval does not write a
result. Change surround clears it and the distance can be edited
again. When the line names problems, no surround is shown, Start
stays off, and the page points at `docs/user/correction-arrows.md`
instead of repeating it.

Why: the surround preview had no page a person could follow, and
the root README is not the place for that guide.

Checked by reading the page against Surround preview in
`agents/architecture/preview.md` and Surround and Conquer in
`agents/architecture/algorithms.md`. The steps are open, read
the line, set Surround distance, approve with Start Algorithm,
then Change surround. `git diff -- docs/user/correction-arrows.md`
is empty. `README.md` already had the readme-default sentence;
this task did not edit it. The page does not describe conquer, a
second surround, or a smoothing control. Status left
`in-progress`.

Summary: No defects. `docs/user/surround.md` follows the surround
preview through approval. The root README and
`docs/user/correction-arrows.md` are unchanged.

Context worth keeping: A person opens the window on Surround and
Conquer, reads the line under the preview, and if it names
problems follows Place correction arrows, with no surround shown
and Start off. Otherwise they set Surround distance, watch the
preview, and choose Start Algorithm. That approval does not write
a result. Change surround, swap, or another mode clears it.
Conquer, a second surround, and a smoothing control are not on
the page. `git diff -- README.md` and `git diff --
docs/user/correction-arrows.md` are empty. The pass is `cr-01.md`.

Result: No defects remain. The named checks passed.

