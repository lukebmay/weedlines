# Priority

When to use: The orchestrator is choosing the next plan.

**Owner:** agent. This file is the ordered list of plans.

Work on `master`. The orchestrator, once assigned, works this
list from the top. How that turn runs is
[`roles/orchestrator.md`](roles/orchestrator.md). An agent with
no role does not open this file.

## Next session

(none — the open plan is waiting on the human)

## Active

| Plan | Notes |
| --- | --- |
| *(none)* | |

## Waiting (human)

| Plan | Why |
| --- | --- |
| [surround-and-conquer](plans/surround-and-conquer/plan.md) | Preflight is in place. The cut subroutines and parameters are not named. |
