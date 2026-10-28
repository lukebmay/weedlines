# User corrections

**Status:** done

## Goal

A person can read how to send correction arrows back to Inkscape
and place them on the document.

## Do

- Add the steps under `docs/user/`. Write them for a person
  following along. The tone rules are
  `agents/installed/documentation.md`.
- Cover the line under the preview, both return actions, and
  import placing the arrows. The behavior is Return actions in
  `agents/architecture/preview.md` and the Result section of
  `agents/architecture/host.md`. Do not copy those parts into the
  page.
- Do not edit the root `README.md`. Do not add a Surround and
  Conquer row. Do not document cut subroutines.

## Checks

- The new page is under `docs/user/`. The root README is unchanged.
- The steps follow the order a person does them, and they name
  both return actions and the import that places the arrows.
- The page does not list Surround and Conquer as a mode.

## Note

Added `docs/user/correction-arrows.md`. A person follows the line
under the preview, then **Return to Inkscape with correction
arrows**, then **Return to Inkscape**, then **Extensions →
Weedlines → Import last result**. The page also says the plain
return alone writes nothing. Import is described as one new
**Weedlines corrections** layer above the document, groups only
for kinds that have arrows, and no design copy. The root README
was not edited. Surround and Conquer is not named.

Checked by reading the page against Return actions in
`agents/architecture/preview.md` and the Result section of
`agents/architecture/host.md`. `git diff -- README.md` is empty.
`rg -n 'Surround and Conquer' docs/user/correction-arrows.md`
finds nothing. Status left `in-progress`.

Summary: No defects. `docs/user/correction-arrows.md` matches the
return actions and the correction import, in the order a person
places the arrows.

Context worth keeping: The person reads the line under the
preview, chooses **Return to Inkscape with correction arrows**
(the line changes and the window stays open), then **Return to
Inkscape** to close, then **Extensions → Weedlines → Import last
result**. Import is one new **Weedlines corrections** layer above
the document, with a group only for each kind that has arrows.
The plain return alone writes no arrows. The root README was not
edited. Surround and Conquer is not named. Re-checked: `git diff
-- README.md` is empty, and `rg -n 'Surround and Conquer'
docs/user/correction-arrows.md` finds nothing. The pass is
`cr-01.md`.

Result: No defects remain. The named checks passed.
