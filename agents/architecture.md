# Architecture

**Owner:** human. Agents may propose edits; apply only with explicit permission.

This file is the **target** architecture: how the product is supposed
to work. After reading it, you should be able to walk a user action
from event to result without guessing which layer owns the change.

Gaps between this file and the running code are closed with a plan.
Do not rewrite this file to describe leftovers.

Words: [`glossary.md`](./glossary.md). When work is complete:
[`acceptance.md`](./acceptance.md). How work is run, including what
is stone: catalog `general.md` and [`general.md`](./general.md) when
this project has one.

## This file can be wrong

This file is what we **currently believe** is the best structure. It
is not a proof. It will change. Parts of it will turn out to be
wrong.

If you think a lock here is **directionally wrong** (the structure
or the product intent, not a leftover in the code), **stop work on
that issue**. Do not paper over it with a second path. Do not silently
edit this file. Do not silently change the code to match a sentence
you suspect is stale. We meet, we decide, then we write the decision
here **with why**: the user-visible problem, what was rejected, what
the lock does, and what it does not apply to.

**Why this paragraph exists:** agents treated exploratory fences and
this file as unchangeable, then hid misses behind fallbacks. A lock
without why cannot be reasoned about when the facts change.

Code that merely lags this file is a plan, not a meeting. A meeting
is for when this file itself looks like the mistake.

## What is being built

Weedlines is an Inkscape extension and shared solvers for **weed cuts**
on vinyl (and similar) designs. Algorithms run in a Start / Cancel
dialog with a live preview.

Extracted from a private Inkcut fork. Stay standalone until the
algorithms are solid. Default mode is `frame`. Do not treat
`island-hop` as production-default until picture QA is accepted.

## Layers

| Piece | Owns | Must not own |
| --- | --- | --- |
| (name) | (facts) | (facts) |

## Notes

(key inner workings / tech choices — keep focused; include **why**)
