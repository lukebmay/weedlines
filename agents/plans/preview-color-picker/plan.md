# Preview color picker

**Rank:** 4

## Goal

The person sets each of the four preview colors with a
color picker and still sees the chosen color. Correction
arrows keep their three fixed colors.

## Guide

- [`../../architecture/preview.md`](../../architecture/preview.md)

## Checks

- Checkerboard light, Checkerboard dark, Weed line
  color, and Default subject color open a color picker.
- The arrow colors stay `#FF00FF`, `#FF6A00`, and
  `#00E5FF`, and they are not picker settings.
- The window does not write a preferences file.
- Undo of a committed preview color still works.
