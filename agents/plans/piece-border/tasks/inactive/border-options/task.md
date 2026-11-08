# Border options

**Status:** waiting

**Blocker:** the human has not named the two option
labels. Do not invent the strings. This task does not
start until the human names both.

## Goal

Both lengths are on the form in every mode, under the
labels the human named.

## Do

Edit `extensions/inkscape/weedlines_dialog/form.py`
only. Show one option for the distance from the piece
size to the inner rectangle, and one option for the
border width, in every mode. Use the labels the human
supplies. Those labels are not in the guide and are
not in this task.

The stored lengths and the change entry come from the
border-paint task. A change to either length uses that
entry. It asks off the GUI thread and repaints the
border. When a surround is showing, the inner distance
also asks for the surround again. The border width
does not. Do not build or clip the rectangles here.

Keep the values while the window is open. A committed
change joins the option history the other lengths
already use. Naming the labels does not bring back
padding, grid spacing, the collar, or the layer name.
Do not remove island-hop.

Do not edit the library, `docs/`, or `README.md`.

## Checks

- The form shows both options in every mode, labeled
  with the human's strings and no others.
- Changing the inner distance asks for the border and,
  when a surround is showing, for the surround.
  Changing the border width asks for the border only.
- Undo and redo cover a committed change to either
  length. Padding, grid spacing, the collar, and the
  layer name stay as they are. Island-hop stays.
- Offscreen, when Qt loads, in
  `tests/test_window_border.py`. No Inkscape.

## Note

The developer writes what changed, why, and how it was checked.
The reviewer then writes the summary, the context worth keeping,
and the result.
