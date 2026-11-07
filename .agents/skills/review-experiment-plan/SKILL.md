---
name: review-experiment-plan
description: Explain a locked experiment plan in Japanese for human review before implementation.
---

# Review Experiment Plan

## Inputs

1. Read context and state. Require phase `PLANNED`, mode `review_experiment_plan`, and a current accepted plan audit.
2. Read only `PLAN_AUDIT.md`, active record, config, scope, and named baseline.
3. Do not read code, raw data, checkpoints, results, full papers, broad repositories, or unapproved references.

## Output

Reply in Japanese. Do not edit files unless explicitly asked for a saved note.

Include:

- Identity: ID, stage, baseline, primary metric, decision mode, and preregistered seed.
- Research fit: overall decision, this stage's role, evidence now/later, and why the scale is adequate. Smoke checks readiness only.
- Plain-language hypothesis: what must be true for the coherent method to work.
- Discrimination: the strongest alternative explanation and whether the minimum evidence separates it from the claim.
- Novelty: why this is not a replay, or what remains unclear.
- Method: baseline/candidate behavior, intervention points, invariants, path/symbol targets, data controls, budget and evaluation rule. Explain expected and conflicting trends plainly.
- Audit: verdict, goal-metric alignment, gaming path, selection/evaluation separation, metric discipline and non-promotion guardrail.
- Profile: agent tier and scientific-risk rationale.
- Read budget: Python counts/reasons for planning and implementation startup; flag unnecessary reads.
- Review risks: confounders, leakage, metric mismatch, inadequate coverage or budget, trivial fragmentation, or unjustified expansion.
- Human decision: approve implementation, accept a `warn` with its caveat, request revision, or defer. A `fail` cannot be approved.

## Boundaries

- Preserve the locked hypothesis, metric, decision mode and criterion, baseline, seed policy, scope, phase read lists, and success rule.
- If the plan looks flawed, recommend a plan revision instead of patching the plan.
- Do not continue into implementation, debugging, training, or evaluation.
