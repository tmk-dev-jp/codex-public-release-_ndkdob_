---
name: audit-experiment-integrity
description: Audit result provenance and plan adherence in REVIEW_REQUIRED, or when an integrity audit is requested.
---

# Audit Experiment Integrity

Speak to the human in Japanese; keep audit files in English.

1. Read `research/CONTEXT.md`, `research/STATE.json`, and the active manifest.
2. Run `python3 scripts/next_agent_action.py --task integrity-audit --id <ID>`. On `build`, run the builder and rerun the gate. For size-only failure, use `$compress-audit-material` in this phase and rerun the gate. On `accept`, use the acceptor without an Agent. On `complete`, route to evaluation. Stop on other errors.
3. Only on `delegate agent=evaluator`, start one fresh read-only Agent. Use bundle metadata, decision facts, accepted plan and implementation audits, and aggregates; inspect changed production source one file at a time only as required.
4. Do not supply prior conclusions. Check provenance, plan adherence, metric validity, split/leakage risk and claim scope. For a comparison, review all reported arms/conditions and replication meaning; scripts own completeness and child-artifact checks.
5. Save only the completed audit template to `review/bundles/<ID>/INTEGRITY_AUDIT.md`.
6. Rerun the gate, require `action=accept`, run `python3 scripts/accept_integrity_audit.py --id <ID>`, and stop. `fail` routes to repair; `pass` or `warn` routes to `$evaluate-experiment`.

If the independent evaluator is unavailable, stop and request human review. Never substitute self-review for the independent verdict.
