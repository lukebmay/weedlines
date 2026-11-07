# Priority

When to use: The orchestrator is choosing the next plan.

**Owner:** agent. This file is the ordered list of plans.

Work on `master`. The next plan is chosen as
[`plans/README.md`](plans/README.md) Rank says. How that turn
runs is [`roles/orchestrator.md`](roles/orchestrator.md). An
agent with no role does not open this file.

A waiting plan stays under its rank. The notes say why. Skip it.

## 5 top

| Plan | Notes |
| --- | --- |
| *(none yet)* | |

## 4 high

| Plan | Notes |
| --- | --- |
| [source-split](plans/source-split/plan.md) | Files past 1000 lines. Behavior preserved. The dialog package may run beside the library tasks. |
| [make-ready](plans/make-ready/plan.md) | Stub waits on source-split's figures package. Cleanup is a design meeting and has no tasks. |
| [surround-doc](plans/surround-doc/plan.md) | The label stage is met. No open task. Skip it. |
| [preview-color-picker](plans/preview-color-picker/plan.md) | Waiting on source-split's dialog package. |
| [start-disabled-reason](plans/start-disabled-reason/plan.md) | Waiting on source-split's run controls file. |
| [control-names](plans/control-names/plan.md) | The pages still say Cancel, Start Algorithm, and Change surround. After surround-doc. |
| [piece-border](plans/piece-border/plan.md) | The sentences are in the guide. Follows the plans above. Do not remove island-hop. |
| [surround-and-conquer](plans/surround-and-conquer/plan.md) | The surround step in the guide. Conquer starts when the human asks. The piece border is not this plan. |
| [_bugs](plans/_bugs/plan.md) | No open task. The directory stays open. |
| [responsive-run](plans/responsive-run/plan.md) | The responsive stage is met. No open task. Skip it. |
| [segment-publish](plans/segment-publish/plan.md) | The publish stage is met. No open task. Skip it. |
| [island-segments](plans/island-segments/plan.md) | The splits stage is met. No open task. Skip it. |
| [window-clarity](plans/window-clarity/plan.md) | The form stage is met. No open task. Skip it. |

## 3 medium

| Plan | Notes |
| --- | --- |
| [run-log-label](plans/run-log-label/plan.md) | Waiting on source-split's dialog package. |
| [design-copy](plans/design-copy/plan.md) | Waiting on control-names task extension-sentence. Same file, `weedlines.py`. |
| [extension-doc-drift](plans/extension-doc-drift/plan.md) | Waiting on surround-doc and control-names. |

## 2 low

| Plan | Notes |
| --- | --- |
| *(none yet)* | |

## 1 optional

| Plan | Notes |
| --- | --- |
| *(none yet)* | |
