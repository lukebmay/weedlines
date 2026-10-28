# Priority

The order of active tasks for surround-and-conquer. A path, then
the reason only when the order would otherwise be a guess.

1. [figure-check](tasks/active/figure-check/task.md)
1. [job-records](tasks/active/job-records/task.md)
1. [figure-overlap](tasks/active/figure-overlap/task.md) — extends the figure-check module
1. [subject-weed](tasks/active/subject-weed/task.md) — extends the figure-check module after overlap targets exist
1. [correction-result](tasks/active/correction-result/task.md) — same job file as job-records
1. [correction-import](tasks/active/correction-import/task.md) — calls the loader correction-result adds
1. [window-gate](tasks/active/window-gate/task.md) — needs the regions and the job records
1. [window-preview](tasks/active/window-preview/task.md) — same dialog as window-gate; paints the arrow paths
1. [window-return](tasks/active/window-return/task.md) — same dialog; writes the correction result
