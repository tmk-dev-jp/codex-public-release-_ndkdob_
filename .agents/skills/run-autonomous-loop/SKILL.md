---
name: run-autonomous-loop
description: Advance one research operation using the state router, stopping at its human decision or operation boundary.
---

# Run Autonomous Loop

Speak Japanese; keep files in English.

1. Read `research/CONTEXT.md` and `research/STATE.json`.
2. Run `python scripts/next_autonomous_step.py`; remember its `operation`.
3. On `blocked`, report the substantive gate; presentation-only errors follow step 7 before stopping.
4. If ready, follow the listed phase skill and its scoped scripts.
5. Rebuild context, rerun the router, and continue only when state, evidence or gate action advanced and the result is `ready` with the same `operation`.
6. Execute at most three phase skills in one operation. Stop before a different operation.
7. For presentation errors, including audit size limits, follow `automation/PRESENTATION_REPAIR.md` in this phase, overriding formatting stops. Corrected output is progress. Stop on no progress, execution/scientific failure, or required human judgment.

Integrated operations:
- `planning`: one frontier plan, a missing bounded novelty check if routed, then one independent plan audit; stop at human review.
- `implementation_review`: one read-only pre-run audit; a `fail` routes to a separate repair.
- `result_review`: integrity audit, then evaluation/finalization only after an accepted `pass` or `warn`.
- `post_result`: memory, direction update with optional result-derived candidates, then one next DRAFT.
- Every other operation remains one phase.

Stop gates:
- Plan decision, human result interpretation, full approval, broad literature permission, or novelty human review.
- Active experiment mismatch, failed phase, missing data setup, or operation change.
- The three-phase limit, even if the operation name did not change.

A phase skill's generic "stop after this phase" returns control here; its human and safety gates still end the turn.

Before any subagent, require its `next_agent_action.py` result to be `delegate`. Use at most one per phase, no panel or retry, and at most one explicit escalation after reclassification. Do not cross operations, train outside scripts, or create parallel experiments.
