---
name: revise-experiment-plan
description: Revise a DRAFT or PLANNED experiment at the user's request, then relock and obtain a fresh audit.
---

# Revise Experiment Plan

Use this when a human requests plan changes before implementation.

## Inputs

1. Read `research/CONTEXT.md`, `research/STATE.json`, `research/GOAL.md`, `research/planning/HYPOTHESIS_POLICY.md`, active `EXPERIMENT.md`, active config, and `SCOPE.json`.
2. If the phase is `PLANNED`, first run `python3 scripts/return_plan_to_draft.py --id <ID>`.
3. If the phase is not `DRAFT` after that, stop and report the blocking phase.
4. Use path listings first. Record indispensable planning reads before opening them. Keep the smallest reasoned `implementation_entry_reads` set for implementation startup; both lists must remain within state budgets.

## Procedure

1. Apply only the human-requested planning change to `Hypothesis`, `Method`, config, and `SCOPE.json`.
2. Recheck the alternative explanation, discriminating evidence, novelty, policy, metric, seed, data controls, baseline/candidate behavior, intervention point, unchanged invariants, and `change_targets`.
3. Recheck Research objective, Study role, Evidence coverage and Scale justification against GOAL. Keep one coherent method comparison, including jointly necessary components; no unrelated changes or silent weakening of the research question.
4. Run `python3 scripts/lock_plan.py --id <ID>` when the revised plan is complete.
5. Run `$audit-experiment-plan` after relocking. Present `$review-experiment-plan` only after the audit is accepted, then stop for a fresh human decision; do not implement.

## Boundaries

- Do not revise a plan after implementation or result inspection.
- Do not update baselines or proposed method records here.
- Do not search papers, read broad repositories, inspect raw data recursively, or run training.
