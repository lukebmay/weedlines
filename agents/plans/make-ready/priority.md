# Priority

The order of active tasks for make-ready. A path, then
the reason only when the order would otherwise be a guess.

ready-marks is done.

1. [ready-writer](tasks/active/ready-writer/task.md)
2. [ready-menu](tasks/active/ready-menu/task.md) — waits on ready-writer, because the child and the reimport use that writer.
