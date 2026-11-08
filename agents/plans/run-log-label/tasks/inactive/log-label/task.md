# Log label

**Status:** waiting

**Blocker:** the human has not named the words on the
label above the log. The guide does not name them.
Do not invent the words. This task does not start
until the human names them.

## Goal

The label above the log uses the human's words, so
the person can see that the pane is the run's output
without reading program words.

## Do

Edit `extensions/inkscape/weedlines_dialog/__init__.py`
only. The label is the `QLabel` whose text is
`Algorithm output (stdout / stderr)`, directly above
`log_view`. Set that text to the words the human
supplies. Those words are not in the guide and are
not in this task. Do not invent them. If they are
still unnamed, stop and do not edit.

Leave the pane. It still shows the run's stdout and
stderr. Do not change `log_view`, what is appended
into it, or which stream is shown.

Do not edit the library. What the library logs does
not change. Do not edit any other file.

## Checks

- The label text is the human's words. It is not
  `Algorithm output (stdout / stderr)`.
- The pane still shows the run's stdout and stderr.
- What the library logs does not change.
- No other words were invented. No file outside
  `__init__.py` changed.

## Note

The developer writes what changed, why, and how it was checked.
The reviewer then writes the summary, the context worth keeping,
and the result.
