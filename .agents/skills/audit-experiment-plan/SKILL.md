---
name: audit-experiment-plan
description: Independently audit a locked plan for metric gaming and research-scale adequacy before human approval.
---

# Audit Experiment Plan

Speak to the human in Japanese; keep audit files in English.

1. Read `research/CONTEXT.md`, `research/STATE.json`, and the active manifest.
2. Run `python3 scripts/next_agent_action.py --task plan-audit --id <ID>`. On `build`, use the builder; on `compress`, use `$compress-audit-material` in this phase; rerun the gate. On `accept`, use the acceptor without an Agent. Stop on other errors.
3. Only on `delegate agent=plan_auditor`, start one fresh read-only Agent. It may read only `PLAN_AUDIT_REQUEST.json` and the output template. Do not supply prior discussion or proposed conclusions.
4. Check source facts versus inference, substantive advance, rival predictions and their faithful mapping into the plan. Check gaming, evaluation separation, baseline comparability, metric discipline and profile. Check Research scale adequacy: goal contribution, essential comparisons, observations, budget and later evidence. Fail unsupported stage claims or missing controls. Smoke is feasibility only. Behaviors, invariants and targets must isolate one coherent method, including jointly necessary components.
5. Permit at most one diagnostic guardrail. It must expose the named gaming path and must never become a second promotion metric.
6. Save only the completed `PLAN_AUDIT.md`, rerun the gate, require `action=accept`, then run `python3 scripts/accept_plan_audit.py --id <ID>`.
7. Present a Japanese review: identity, objective, stage, coverage, hypothesis, discriminating evidence, novelty, method, verdict, gaming, guardrail, profile, read budget, risks and human decisions. Stop. `pass`/`warn` need a human decision; `fail` requires revision. No second skill for this presentation.

The request plus template must remain within 9,000 characters and the completed audit within 250 words. Do not browse code, data, results, papers, or files outside the bundle. Do not create a reviewer panel, retry, fall back to self-review, edit the plan, or implement it. If the auditor is unavailable, stop.
