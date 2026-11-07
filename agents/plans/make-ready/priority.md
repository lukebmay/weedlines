# Priority

The order of active tasks for make-ready. A path, then
the reason only when the order would otherwise be a guess.

1. [ready-marks](tasks/active/ready-marks/task.md)
2. [ready-writer](tasks/active/ready-writer/task.md) — waits on ready-marks, because the writer places the label points from that result.
3. [ready-menu](tasks/active/ready-menu/task.md) — waits on ready-writer, because the child and the reimport use that writer.
