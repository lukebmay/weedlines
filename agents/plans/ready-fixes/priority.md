# Priority

The order of active tasks for ready-fixes. A path,
then the reason only when the order would otherwise
be a guess.

1. [propose-span](tasks/active/propose-span/task.md)
1. [ready-group](tasks/active/ready-group/task.md)

These two name different files.

1. [propose-corner](tasks/active/propose-corner/task.md)
1. [propose-join](tasks/active/propose-join/task.md)
1. [propose-weld](tasks/active/propose-weld/task.md)

Those three share `src/weedlib/propose.py` and
`tests/test_propose.py` with propose-span. They
stay serial.

1. [proposal-window](tasks/active/proposal-window/task.md)

It waits until the proposal tasks and ready-group
are done. It shows the paths they return and calls
the Ready fixes writer.

1. [open-proposals](tasks/active/open-proposals/task.md)

It waits until the proposal window exists.
