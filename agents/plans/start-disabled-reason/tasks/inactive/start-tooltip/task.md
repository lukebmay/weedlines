# Start tooltip

**Status:** done

## Goal

When a defect disables Start, the person can tell why from
that button's tooltip. The status can still read ready.

## Do

`extensions/inkscape/weedlines_dialog/run_controls.py` owns
Start and the status. Put the tooltip on the button whose
object name is `start`.

When that Start is disabled because the figure check found
a defect, the tooltip names each marked problem that is
present. The names are dangling ends, figure overlaps, and
self-overlaps. Those words already live on the defect line
in `extensions/inkscape/weedlines_dialog/return_line.py`.
Use that list. Join more than one the way the line already
does. Do not add a reason of your own, and do not keep a
second list of the names in run_controls.

Do not change the defect line, the two return actions, or
their place under the preview. Do not edit the package
index.

The status words stay ready, working, paused, and done. A
phase may still follow working or paused, as it does now.
With a defect and no step running, the status still reads
ready. Do not add a fifth status word.

Start disabled because a step is running is unchanged.
That includes Restart while the step is running. Do not
put this tooltip on that disable, and do not leave it
there once the check is clear. Conquer's Start, object
name `conquer-start`, stays disabled and does not get
this tooltip.

Cover every path that enables or disables `start`,
including a border ask and Clear All while a step is
stopping. Do not split run_controls.py.

The guide is Return actions in
`agents/architecture/preview.md` and Run in
`agents/architecture/runtime.md`. Do not edit the guide.

Tests stay in the files that already cover this window.
Extend `tests/test_window_return.py` for the defect
tooltip, the line under the preview, and a clear check.
Extend the running-step case in
`tests/test_window_timing.py`. Do not add a test file.

## Checks

Offscreen, when Qt loads. No Inkscape.

- With a defect, Start is disabled, the status is ready,
  and the tooltip names each marked problem that is
  present and no other kind.
- The line under the preview stays in the layout. With a
  defect, both return actions are still there.
- A clear check leaves Start enabled, with no defect
  tooltip, and the status ready.
- While a step is running, Start stays disabled as it
  does now, the status is working, and Start has no
  defect tooltip.
- `pytest tests/test_window_return.py tests/test_window_timing.py`
  passes. A window test skips only when Qt is missing.

## Note

Start names the marked problems in its tooltip. The names are the
ones already on the defect line: dangling ends, figure overlaps,
and self-overlaps, joined the same way. `run_controls` asks the
return line for that text and does not keep a second list. The
tooltip is set on every path that enables or disables Start,
including a border ask and Clear All while a step is stopping.
It is shown only when a defect is blocking Start and no step is
running or stopping. The status stays ready in that case. A
running step, including Restart, still disables Start with no
defect tooltip, and the status stays working. A clear check
leaves Start enabled with an empty tooltip. Conquer's Start is
unchanged. The defect line and the two return actions are
unchanged. A disabled Start can show the tooltip.

Checked offscreen, no Inkscape, with `QT_QPA_PLATFORM=offscreen
python3 -m pytest tests/test_window_return.py
tests/test_window_timing.py`: 15 passed.

The reviewer then writes the summary, the context worth keeping,
and the result.

## Summary

No defects. When a defect blocks Start and no step is
running or stopping, the tooltip names the marked problems
that are present. The words are dangling ends, figure
overlaps, and self-overlaps, joined the way the defect
line already joins them. The line still has the swatches.
The tooltip does not. `run_controls` asks the return line
for that text and does not keep a second list. A border
ask keeps the tip. Stopping, a running step, and Restart
leave it empty. A clear check leaves Start enabled with
an empty tip. The status stays ready when the defect is
the reason, and working while a step runs. Conquer's
Start is unchanged. The defect line and the two return
actions are unchanged.

## Context worth keeping

The names stay in `_KIND_WORDS` in `return_line.py`.
`_marked_problems` walks that list and `_join_words` is
the same join the defect line uses. One name stands
alone, two use `and`, three use a comma and `, and`.
`_marked_problem_text` returns that plain string, or
empty when `check` is None or no kind is present.
`run_controls.py` has no copy of the words.

`_sync_start_tip` runs from `_sync_start_button`, from
`_relax_border_controls`, and from Clear All while a
step is stopping. A border ask is not a run, so a defect
tip stays and the status stays ready. `aborting`, or
`busy` with any other ask, clears the tip. The opening
gate sets `blocked` before the check. `check` is still
None then, so the text stays empty until classify stores
the kinds and `set_controls` runs.

A disabled button does not show a tooltip on this Qt
unless `WA_AlwaysShowToolTips` is set. The attribute is
on the `start` button. A hover then shows the tip. Do
not drop the attribute. Conquer's Start never gets it.
The status words were not edited. The package index and
the guide were not edited.

## Result

No defects remain. The named checks passed.
`QT_QPA_PLATFORM=offscreen python3 -m pytest tests/test_window_return.py tests/test_window_timing.py`:
15 passed in 5.18s. Qt loaded through enaml (PyQt 5.15.11,
Qt 5.15.14). Nothing skipped. The tests did not start
Inkscape. The pass is `cr-01.md`.
