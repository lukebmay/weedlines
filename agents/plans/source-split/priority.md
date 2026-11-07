# Priority

The order of active tasks for source-split. A path, then
the reason only when the order would otherwise be a guess.

keep-figures, surround-package, and dialog-package name
different files. They may run together.

1. [keep-figures](tasks/active/keep-figures/task.md)
2. [surround-package](tasks/active/surround-package/task.md)
3. [dialog-package](tasks/active/dialog-package/task.md)
4. [solvers-package](tasks/active/solvers-package/task.md) — waits on keep-figures, because `solvers/__init__.py` re-exports the public keep names from `weedlib.keep`.
