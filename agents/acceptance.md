# Product checks

**Owner:** human. Agents may propose edits; apply only with explicit permission.

This file is an incomplete list of what the product should do, written
so a test can confirm it. The handbook calls it acceptance: the checks
that must hold before work is done. It is not the design. Bugs live in
[`issues.md`](./issues.md).

When a plan ships and gets archived, ask human for approval if you believe any of the plan acceptance criteria stay durable and should be promoted into this document.

When a new plan would change old behavior, **amend this file** (with permission)
before or with the plan.

## Required minimum

- (Fill in the user-visible gestures that must still hold after any change.)
- Tests confirm these gestures; they are not a substitute for them.
- A regression is a test that fails without the fix and passes with it. Do not keep a second ledger of failure classes.

## Notes

Confirm the way [`testing.md`](./testing.md) (project or catalog) describes.
