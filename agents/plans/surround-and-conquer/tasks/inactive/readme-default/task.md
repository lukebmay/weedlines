# Readme default

**Status:** done

## Goal

The root README states that the default mode is Surround and
Conquer, and it does not gain a longer guide.

## Do

- In `README.md`, change only the sentence that begins "Default
  mode is" and names frame. The new sentence states that the
  default mode is Surround and Conquer.
- Leave the following sentence, the mode table, and the rest of
  the file. Do not add a row or any steps.
- Do not edit `docs/` or any code.

## Checks

- That one sentence names Surround and Conquer as the default.
- The island-hop sentence under it is unchanged. No mode row and
  no guide text were added.
- `docs/` has no diff from this task.

## Note

Changed the one sentence in `README.md` that began "Default mode
is" and named `frame`. It now says the default mode is Surround
and Conquer. The island-hop sentence under it, the mode table,
and the rest of the file are unchanged. No row and no guide text
were added. `docs/` and code were not edited.

Why: the window opens on Surround and Conquer, and the root
README still named `frame` as the default.

Checked on `master`. `git diff -- README.md` is that one
sentence. The next sentence is still "Do not treat `island-hop`
as production-default until picture QA is accepted." The mode
table is still `frame`, `grid`, and `island-hop`. `git diff --
docs/` is empty. `git status --short` shows only `README.md`.
Status left `in-progress`.

Summary: No defects. The one README sentence now names Surround
and Conquer as the default. The island-hop sentence, the mode
table, and the rest of the file are unchanged.

Context worth keeping: `git diff -- README.md` replaces
`` `frame` `` with Surround and Conquer. The next sentence is
still "Do not treat `island-hop` as production-default until
picture QA is accepted." The mode table is still `frame`,
`grid`, and `island-hop`. `git diff -- docs/` is empty, and no
code file changed. Untracked `docs/user/surround.md` belongs to
the user-surround task; do not revert it. The pass is
`cr-01.md`.

Result: No defects remain. The named checks passed.
