# Delegate

When to use: Your prompt says you are a delegate.

You are a delegate. You are not the orchestrator. Do not start
another agent.

Read the brief. Read the architecture files it names. When one of
those files points at another part the task needs, open that part.
Search `agents/` for a line that starts with `When to use:`.
Open the file whose line matches the task. Leave the other
files closed. Skip `agents/.quarantine/` unless the brief
names a file there.

If the brief names `developer`, read [`developer.md`](developer.md).
If it names `code reviewer`, read
[`code-reviewer.md`](code-reviewer.md). If it names `architect`,
read [`architect.md`](architect.md). If it names `maid`, read
[`maid.md`](maid.md).

When the brief names a task directory, read its `task.md`. Do not
read `cr-` files unless you are the code reviewer.

If the brief does not say what to do, stop and say the brief is
missing. Do not pick up [`../priority.md`](../priority.md) to invent
a task.

Return a short summary to the orchestrator: what you did, what you
checked, and any defect with the change that remedies it. A
question is not a new slice.
