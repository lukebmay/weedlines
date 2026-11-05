# Priority

The order of active tasks for responsive-run. A path, then
the reason only when the order would otherwise be a guess.

1. [surround-checks](tasks/active/surround-checks/task.md) — calls the hook from progress-focus
2. [solver-checks](tasks/active/solver-checks/task.md) — same hook, different module from the surround
3. [figure-checks](tasks/active/figure-checks/task.md) — same hook, different module from the solvers
4. [figure-check-run](tasks/active/figure-check-run/task.md) — dialog file, after the library checks exist
5. [surround-run](tasks/active/surround-run/task.md) — same dialog file as the solver run
6. [solver-run](tasks/active/solver-run/task.md)
