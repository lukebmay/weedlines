# Extension doc drift

**Rank:** 3

**Stage:** directions

## Goal

The extension doc describes this repo's extension. It
stops sending the person to the old Inkcut extension.

## Guide

- [`../../architecture/host.md`](../../architecture/host.md)
- [`../../architecture/install.md`](../../architecture/install.md)

## Checks

- `docs/inkscape-extension.md` does not tell the person
  to open Extensions → Inkcut, and it does not name
  `inkcut.weedlib` as this extension. It does not tell
  the person to run `inkcut install-plugin` or to
  symlink `inkcut_weeds.py`.
- The menu it names is the menu in the host part. It
  does not invent an entry.
- It does not redo the run-control names, the Apply
  sentence, the join-gap sentences, or the units
  section.
- It does not add piece-border labels, a log label, a
  cavern measure, or a design-copy sentence.
- The product does not change.
