Repaired the audit's P2 finding.

- `scripts/sycophancy_study.py:366–401`: provider failure now takes precedence while separately retaining exposed tool activity and runtime metadata. Raw envelopes remain unchanged.
- `tests/unit/test_sycophancy_study.py:197–235`: regression covers explicit and envelope-reported failures, mandatory pause, immutable original results, and dispatch of only the next unused item after external resolution.

Verification: **47 tests passed in 7.24s**; scoped Ruff and whitespace checks passed. No model calls, real study artifacts, or audit-record edits.
