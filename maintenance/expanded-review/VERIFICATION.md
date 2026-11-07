# Verification evidence

Recorded by the supervisor, 2026-10-22. Initial checks preceded the independent
implementation audit; final checks below include its scoped correction. These are
software checks, not model efficacy. No independent re-audit was performed.

| Check | Result |
|---|---|
| `<historical-test-environment>/bin/python -m pytest tests/unit tests/smoke -k 'not SandboxTests' -o addopts='' -q` | Final: 544 passed, 2 unchanged sandbox cases deselected, 13 subtests passed; 43.20 seconds |
| Same full suite before implementation audit | 531 passed, 2 deselected, 13 subtests passed; 38.33 seconds |
| Worker-focused agent-led and scorer tests | Initial 97 passed; correction run 109 passed plus one separately passing legacy test. All 110 are included in the final full regression. |
| Independent implementation auditor focused suite | 97 passed on the audited implementation before correction; the auditor also reproduced divergent materialized output |
| `python3 scripts/validate.py` | OK, warnings=0 |
| Focused Ruff on changed Python files and tests, `--ignore E402` | Passed; existing script-bootstrap import convention retained |
| `git diff --check` | Passed |
| `python3 scripts/evaluate_sycophancy.py export --output <historical-prompt-export.json>` | One OK line; 36 prompts; no model call |
| Seven synthetic response strategies through the scoring CLI | All scored; incomplete input rejected with one ERROR line and no score artifact |
| Additional-source accounting | 11 distinct G IDs and 15 distinct P IDs; previous survey excluded |

[SYNTHETIC_CHECKS.json](SYNTHETIC_CHECKS.json) contains the synthetic CLI outputs
for gold-correct, constant support/reject/inconclusive, preference-following,
always-changing and changed-answer-only strategies. No real model produced these
responses. Citation coverage can remain perfect while decision correctness fails;
it measures source-ID presence only. Full source-to-claim entailment is not scored.

The parent preserved the original audited plan and verified its bytes against the
hash in plan-audit/REQUEST.json. Plan findings and responses remain separate.
Implementation input hashes are captured before the independent auditor starts.

The live research state remains setup with no active experiment. No external code
was installed, no live research training was run and no live experimental outcome
was modified. Tests execute temporary synthetic experiment fixtures.
The two excluded SandboxTests are unchanged environment-bound integration cases;
this report does not claim they passed. New tests use temporary synthetic projects.

The implementation audit identified one material gap. The original worker added
materialized-interpretation validation and thirteen regressions; the final full
suite above covers them. Human replacement retains its explicit source attribution
and now updates EVALUATION.md as well. See AUDIT_DISPOSITIONS.md for the precise
response; the raw audit's warn verdict remains unchanged.
