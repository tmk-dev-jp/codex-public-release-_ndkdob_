Completed scoped implementation.

Changed:
- Acceptance/provenance: `research_decision.py`, `accept_human_interpretation.py`, `approve_plan.py`.
- Shared interruption guard: new `decision_integrity.py`, `workflow.py`, ordinary autonomous/unattended routers.
- Diagnostic: new `evaluate_sycophancy.py`, 12-case fixture, scorer tests.
- Expanded `test_agent_led_loop.py` and `DECISIONS.md`.

Verification:
- **97 tests passed**: 79 agent-led, 18 scoring.
- Focused Ruff passed, ignoring existing bootstrap E402.
- Scoped `git diff --check` passed.
- Export CLI produced one `OK` line and 36 prompts.

Guard inventory: `require_active` checks before phase validation; covers direct human approval/interpretation, implementation gating, revision, finalization and transitions. Autonomous/unattended routers check before routing or state writes; agent-led routing inherits that early guard.

Evidence includes invalid-response-before-intent, 16 fault boundaries, mismatched phases, completed-evidence tampering, missing new intent, replay rejection, facts/audit preservation, and valid inconclusive finalization. Direct agent interpretations require canonical dispatched proof and exact bytes; saved evaluation includes provenance.

Limits: detection only—no rollback/replay, concurrent-writer protection, power-loss durability or host authentication. Legacy completed receipts remain compatible. Synthetic diagnostic tests establish scorer behavior, not model efficacy. Full regression and independent implementation audit remain with parent.
