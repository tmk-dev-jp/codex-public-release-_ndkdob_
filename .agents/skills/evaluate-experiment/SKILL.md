---
name: evaluate-experiment
description: Interpret trained results against the locked plan after required audits, then finalize supported claims.
---

1. Run `python3 scripts/next_agent_action.py --task evaluation --id <ID>`. On `build`, run the named builder and rerun the gate. On `accept` or `finalize`, run the corresponding script without an Agent. Stop on `blocked` or `ERROR`.
2. Read the active record, `DECISION_FACTS.json` including research_focus, audits, metrics, baseline and manifest. Follow `automation/RESEARCH_FOCUS.md`. No source, tests, snapshots, checkpoints or batch histories.
3. Treat metric identity, direction, baseline value, oriented effect, and `Mechanical rule status` as authoritative machine facts. Never recompute or override them. For `trend_requires_interpretation`, use only the preregistered rule and classify the pattern as expected, weak, opposite, mixed, or uninformative.
4. In `Supported scope` answer the research question and novelty claim; put untested or confounded differences in `Unsupported or missing evidence`. For comparisons, use all condition contrasts in the facts; a favorable mean cannot erase failed controls or opposing conditions. Training repeats on one dataset are not independent dataset replications.
5. Fill `Decision-rule assessment` with that comparison. Address the plan audit's gaming path and guardrail, then separate support, contradiction, confounders, audit warnings, resource cost, and uncertainty. Trend evidence cannot establish an unmeasured magnitude.
6. If required trend observations are absent from aggregate artifacts or the pattern is ambiguous, route to `$request-human-result-interpretation`; do not guess, add a post-hoc pattern, or change the locked rule.
7. Keep `Conclusion` plus `Issues and Next Direction` within 400 words. On `local`, fill only those sections, copy the exact machine status, rerun the gate, and finalize only on `action=finalize`. On `delegate`, use one read-only `evaluator`, save `EVALUATION.md`, rerun the gate, require `action=accept`, and run `accept_evaluation.py`.
8. Run `python3 scripts/finalize_experiment.py --id <ID>` only on `action=finalize`, then stop.
