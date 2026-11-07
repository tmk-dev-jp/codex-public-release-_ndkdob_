---
name: review-experiment-result
description: Explain a completed or evaluated experiment in Japanese when the user requests result review.
---

# Review Experiment Result

Use this for human-facing review of experiment evidence. It does not change files by default.

## Inputs

1. Read `research/CONTEXT.md`, `research/STATE.json`, `experiments/DIGEST.md`, and the active or latest completed `EXPERIMENT.md` named by context.
2. Read aggregate `metrics.json` and runtime `manifest.json` only when the experiment is not finalized and those paths are named by the experiment manifest.
3. Do not inspect checkpoints, batch histories, raw data, implementation code, full papers, or broad completed experiment folders.

## Output

Reply in Japanese. Include:

- Result identity: experiment ID, stage, metric, baseline or none, and seed.
- Evidence summary: primary result, locked threshold comparison or trend assessment, and decision.
- Interpretation: what the result says about the proposed method and core hypothesis.
- Caveats: confounders, data leakage risk, metric mismatch, resource limit, or uncertainty.
- Recommended human action: accept the conclusion, request `$update-research-direction`, request a plan revision, run no further experiments, or defer.
- If the result cannot be interpreted reliably from aggregate metrics alone, recommend `$request-human-result-interpretation` instead of guessing.
- If results suggest a new hypothesis, distinguish it from supported conclusions and recommend `$update-research-direction` to record a candidate with evidence references, even if the queue is nonempty. Review alone does not save it or authorize another experiment.

## Boundaries

- Do not change locked metrics, decision mode or criterion, baselines, seed policy, or conclusions after results are visible.
- Do not update baselines. If the result is promising, recommend updating `research/PROPOSED_METHOD.md` through `$update-research-direction`.
- Do not select or create the next experiment.
