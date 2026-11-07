---
name: review-research-loop
description: Review research-loop skills or workflow defects when the user requests an audit or maintenance review.
---

# Review Research Loop

Review only the requested surface. Report findings in Japanese with exact paths, observed behavior, impact, and focused verification.

## Choose the evidence

- Skill or prompt review: list paths and descriptions first; read relevant bodies and direct references only. Check selection overlap, duplication, unnecessary reads, confirmation loops, and completion. No Python or research state is needed unless a finding depends on runtime behavior.
- Routing or gate defect: read context, state, the relevant router branch, phase script, and matching skill. Trace `mode -> skill -> script -> resulting mode`; inspect validator clauses only for affected contracts.
- Recurring failures: add only relevant compact digest, ledger, or failure-memory entries.

Preserve plan locks, data controls, independent scientific audits, evidence provenance, human research decisions, and read/token budgets. Distinguish enforced contracts from optional conventions; make references conditional on the task.

## Finish

- Review-only request: return ranked findings and proposed fixes; leave files unchanged.
- User also requests improvements: use `$apply-research-loop-improvement` for that scope in this turn. Existing authorization is sufficient; another message or exact skill spelling is unnecessary.
- A recommendation alone is not permission to implement. Ask only about decisions outside the requested scope or changes affecting an active experiment's locked contract.
