# Planning scope

- Use `$plan-experiment` and stop after the plan is locked.
- Read `research/CONTEXT.md`, `research/GOAL.md`, `research/planning/HYPOTHESIS_POLICY.md`, `experiments/DIGEST.md`, the active record, config, and scope only.
- Start from GOAL's evidence strategy. Require adequate comparisons and scale before minimizing cost; record objective, study role, coverage and scale justification.
- Lock falsifier, baseline, primary metric, threshold/trend rule, novelty, policy, data controls, budget and promotion rule.
- Reject candidate hypotheses that violate `research/planning/HYPOTHESIS_POLICY.md`; ask for policy or goal revision if no useful candidate remains.
- Before locking, check briefly that the plan is not a replay. Planning may add one tiny obvious-keyword prior-work search: titles/abstracts/snippets only, 2-3 high-similarity hits max, no downloads/full papers.
- Test one coherent method, including jointly necessary components. Keep essential controls; avoid exploratory ablations, seed searches and fine sweeps.
- One active hypothesis; optional `comparison` groups required arms, conditions and seeds in one config. Smoke checks feasibility only.
- Name exact files in `SCOPE.json`; do not use directory globs.
- Do not implement, debug, train, inspect checkpoints, or revise visible results.
