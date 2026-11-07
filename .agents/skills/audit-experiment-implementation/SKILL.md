---
name: audit-experiment-implementation
description: Independently audit a locked pilot or full implementation before execution.
---

# Audit Experiment Implementation

Speak to the human in Japanese; keep audit files in English.

1. Read `research/CONTEXT.md`, `research/STATE.json`, and the active manifest.
2. Run `python3 scripts/next_agent_action.py --task implementation-audit --id <ID>`. On `build`, run the builder and rerun the gate. For size-only failure, use `$compress-audit-material` in this phase and rerun the gate. On `accept`, use the acceptor without an Agent. Stop on other errors.
3. Only on `delegate agent=evaluator`, start one fresh read-only Agent. Use the request, implementation delta, accepted plan audit, plan, config, and scope; inspect snapshot files one at a time only when required.
4. Treat hashes and observed changed symbols as machine facts. Judge whether the changes test the planned novelty and research question at the intervention point while preserving invariants; also check split/leakage, optimization, metrics, reproducibility, and minimality.
5. Record `pass`, `warn`, or `fail` with concrete evidence. A warning must not invalidate scientific results; otherwise use `fail`.
6. Save only the completed `IMPLEMENTATION_AUDIT.md`, rerun the gate, require `action=accept`, run `python3 scripts/accept_implementation_audit.py --id <ID>`, and stop.

`pass` or `warn` routes to `$run-experiment`; `fail` routes to `$debug-failure`. If the independent evaluator is unavailable, stop. Never substitute self-review, change code, weaken the plan, or run training here.
