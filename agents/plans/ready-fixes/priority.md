# Priority

The order of active tasks for ready-fixes. A path,
then the reason only when the order would otherwise
be a guess.

1. [propose-span](tasks/active/propose-span/task.md)

[ready-group](tasks/inactive/ready-group/task.md) is done.

1. [propose-corner](tasks/active/propose-corner/task.md)
1. [propose-join](tasks/active/propose-join/task.md)
1. [propose-weld](tasks/active/propose-weld/task.md)

Those three share `src/weedlib/propose.py` and
`tests/test_propose.py` with propose-span. They
stay serial.

1. [proposal-window](tasks/active/proposal-window/task.md)

It waits until the proposal tasks are done.
ready-group is done. It shows the paths they
return and calls the Ready fixes writer.

1. [open-proposals](tasks/active/open-proposals/task.md)

It waits until the proposal window exists.
