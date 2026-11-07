# Diagnostic expansion status

> Public distribution note: The historical Luna run and Qwen preparation records
> are excluded from this template. Counts and verification statements below
> describe the original maintenance work; the omitted inputs, raw logs and
> frozen manifests cannot be inspected or reverified from this distribution.
> No historical results or hashes were regenerated. See
> [public distribution scope](../../review/sycophancy/PUBLIC_DISTRIBUTION.md).

Latest steering: before any model response, the user requested Luna at max
reasoning instead of Qwen3.8. LUNA_AMENDMENT.md records the authorized runtime
change. The Qwen preparation status below remains historical zero-attempt evidence.
Current execution status and the latest software checks are recorded separately
in [LUNA_RESULT.md](LUNA_RESULT.md).

The user accepted the next improvement plan and then reported Qwen3.8 offline.
This maintenance work implements and prepares the fixed comparison. No Qwen call,
fallback model call or fabricated human semantic review is permitted during the
known outage. Offline status is an external dependency, not an observed failure
of the tested model or guidance.

## Authorized comparison

- Twelve labeled synthetic families: six user-pressure and six peer-pressure.
- Seventy-two prompts per arm; 144 attempts maximum across both arms.
- A uses current independent-judgment guidance; B omits only that guidance.
- Same evidence, audit authority, contribution task, output schema and settings.
- Primary conformity changes and condition-specific correctness are separate.
- Human assessment distinguishes source entailment from discriminating predictions
  and evaluates whether each response correctly assesses these properties.
- All semantic uncertainty remains visible and prevents a favorable conclusion.

The frozen definitions and limits are in PLAN.md. Earlier research already exists
in ../expanded-review/SURVEY.md and SYCOPHANCY_SOURCES.md; this increment adds no
literature search, provider grid, production policy layer or research-state change.

## Review evidence

The one independent read-only plan auditor returned WARN. Its unchanged report is
PLAN_AUDIT.md. All four findings were incorporated before implementation; see
AUDIT_DISPOSITIONS.md. The exact audited plan is plan-audit/PLAN.reviewed.md.
The prior scientific-contribution review that inspected nothing remains preserved
in ../AI_DISCOVERY_REVIEW_STATUS.md and is not evidence of this implementation.

The implementation worker reported 45 focused tests and scoped Ruff passing. Its
unchanged summary is implementation/RESULT.md. During synthetic testing it found
and repaired a constant-answer comparison counterexample through a documented
pre-output plan amendment; see AUDIT_DISPOSITIONS.md.

Parent integration checks after the audited P2 correction:

- `<historical-test-environment>/bin/python -m pytest tests/unit tests/smoke -k
  'not SandboxTests' -o addopts='' -q`: 677 passed, 2 existing sandbox-dependent
  cases deselected, 13 subtests passed in 47.48 seconds. Before correction, the full
  suite also passed 675 tests; the two additional cases reproduce the audit finding.
- `python3 scripts/validate.py`: OK, zero warnings.
- Focused Ruff on the two runtime files and two test files with `--ignore E402`:
  passed. E402 preserves the existing CLI import bootstrap.
- `git diff --check`: passed.
- SHA-256 comparison: the five live research inputs, original v1 fixture,
  independent-judgment policy and scientific-contribution contract are unchanged.

The sole independent implementation auditor returned WARN for provider-failure
precedence when tool activity is also exposed. IMPLEMENTATION_AUDIT.md preserves
the raw report. The original implementer repaired it and added two regressions;
47 focused tests passed. The parent inspected the correction and ran the final
full checks above. No independent re-audit or replacement reviewer was used.

## Historical Qwen preparation, superseded by the requested Luna runtime

The omitted Qwen preparation directory contained frozen fixture, policy,
settings, rubric, requests and hashes. Historical preparation and status commands succeeded:

- Planned: 144, with 72 requests per arm (30 user and 42 peer).
- Attempts: 0; all 144 requests remain not-dispatched.
- Returned-valid, returned-invalid, provider-error, dispatched-without-result: 0.
- Scorable: false; actual human semantic review is pending.

At this preparation stage, Qwen3.8 was offline according to the user. No call,
availability probe, retry or model substitution had been made. No real provider
envelope or human judgment was available. The adapter-free raw-envelope workflow
had synthetic coverage only; actual provider behavior remained unverified.

The original next step was to wait for availability, preserve each attempt in
one comparison and obtain a designated human's assessment. The user's later
Luna instruction supersedes that runtime choice; this historical section does
not direct a Qwen restart. Follow LUNA_RESULT.md and
human/SYCOPHANCY_EVALUATION.ja.md for the current outcome. There is no scheduler
or automatic restart. Software verification alone supports no observed reduction
in sycophancy or general scientific effectiveness.
