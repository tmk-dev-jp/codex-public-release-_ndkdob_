---
name: run-one-unattended-loop
description: Run one explicitly requested experiment through direction update without intermediate decisions.
---

# Run One Unattended Loop

Explicit-only. Report in the user's language; keep files in English.

## Authorization

- Require an explicit current request for this skill or one unattended loop.
- `STATE.unattended_loop` stores recovery progress, never permission. Pass `--explicit-user-request` only for the current request.
- Invocation preapproves one target, its runs and bounded hypothesis replenishment. Do not expand its hypothesis, cells or budget. Full training, broader sources, unresolved data choices, execution retries and another experiment need separate authority.
- Phase skills are subordinate to this sole top-level skill.

## Route

1. Read `research/CONTEXT.md` and `research/STATE.json`.
2. Run `python3 scripts/next_unattended_loop_step.py --explicit-user-request`. On `replenish-hypotheses`, use `$replenish-research-hypotheses` (including goal-scoped 2-3-hit search). Reroute; on `create-target`, use `$select-next-experiment`; the next call binds its ID.
3. On `run-phase`, follow the listed skill once, including routed novelty preparation. Evidence or gate changes count as progress. Rerun with `--explicit-user-request`; `--target <ID>` is optional.
4. On `approve-plan`, require cleared novelty and current plan-audit `pass`; `warn`/`fail` blocks. Run `python3 scripts/approve_plan.py --id <ID> --source explicit_unattended_loop`.
5. Finish on `complete` with no active experiment and mode `select_experiment`; never select another.

## Stop

For presentation errors follow `automation/PRESENTATION_REPAIR.md` in this phase. Preserve findings and reuse the report.

Stop on unresolved facts, mismatch, no progress after correction, substantive validation failure, `FAILED`, uncleared novelty, unavailable evaluator, human interpretation or broader source need. Full approval gates execution only.

Delegate only on `next_agent_action.py` returning `delegate`. Never retry execution, alter a locked plan, manufacture judgment, bypass scripts, expand scope or start background work.
