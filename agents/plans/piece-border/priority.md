# Priority

The order of active tasks for piece-border. A path, then
the reason only when the order would otherwise be a guess.

`surround-clip` and `border-cuts` name different files.
They may run together. `border-paint` follows both.

1. [surround-clip](tasks/active/surround-clip/task.md) — may run with border-cuts
2. [border-cuts](tasks/active/border-cuts/task.md) — may run with surround-clip
3. [border-paint](tasks/active/border-paint/task.md) — after the clip and the cuts
