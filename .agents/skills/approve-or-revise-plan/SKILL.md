---
name: approve-or-revise-plan
description: Record a human decision on a reviewed experiment plan and complete its authorized implementation or revision.
---

# Approve Or Revise Plan

Use this after the human receives a locked-plan review from planning, revision, or `$review-experiment-plan`.

## Inputs

1. Read `research/CONTEXT.md`, `research/STATE.json`, active `EXPERIMENT.md`, `PLAN_AUDIT.md`, manifest, config, and `SCOPE.json`.
2. Confirm the active phase is `PLANNED`.
3. Ask only if the human decision is ambiguous: approve implementation, revise the plan, or cancel/defer.

## Procedure

- A plan-audit `fail` cannot be approved. A `warn` needs an explicit human acceptance of its caveat. Unattended approval accepts only `pass`.
- If approved, run `python3 scripts/approve_plan.py --id <ID>`, then complete `$implement-experiment` in this turn. Stop after `mark_implemented.py`; do not execute. Honor a request to record approval only.
- If revision is requested, run `python3 scripts/return_plan_to_draft.py --id <ID>`, then complete `$revise-experiment-plan`. Relock, run `$audit-experiment-plan`, present the revised review, and stop for a fresh human decision.
- If canceled or deferred, do not change scientific fields. Report that no implementation should start until a new decision is made.

## Boundaries

- Never implement without an explicit approval; never train, evaluate, or debug in this operation.
- The approved path must preserve the locked plan and use the scoped, budgeted implementation reads.
- The revision path may edit planning fields only after the script returns the plan to `DRAFT`; it requires new approval after relocking.
