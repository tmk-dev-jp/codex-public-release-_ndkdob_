Correction complete in three files:

- `decision_integrity.py`: verifies current agent evaluation provenance, exact saved/materialized interpretation bytes, copied Conclusion/Issues sections and manifest decision against the accepted response.
- `accept_human_interpretation.py`: human replacement also updates `EVALUATION.md`, retaining honest source attribution.
- `test_agent_led_loop.py`: 13 new regressions covering the reproduction, individual tampering, unchanged evidence, unrelated record edits, explicit human replacement and legacy compatibility.

Validation: **109 focused tests passed**, then the additional legacy regression passed separately; **110 tests covered overall**. Focused Ruff and scoped diff checks passed.

No audit records, live research state or unrelated files changed. Parent can proceed with final integration checks.
