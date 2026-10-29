# User surround

**Status:** in-progress

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

The developer writes what changed, why, and how it was checked.
The reviewer then writes the summary, the context worth keeping,
and the result.
