# Prospective citation-format clarification

## Authorization and observed problem

The user requested "Plan and modify" after the Luna max comparison completed with
96 valid-format and 48 invalid-citation responses. This authorizes this maintenance
change and local verification. It does not launch another model comparison.

The v2 exporter displays source headings as `[ID]`, but its response schema says
only `source ID`. The validator accepts exact bare source keys. Forty-seven failed
responses used bracketed versions of known keys; one also cited prompt section
labels. These are format observations, not a judgment of substantive correctness.

## Locked change

1. Clarify the shared v2 export at its existing source. Enumerate the allowed bare
   citation strings for each case from the same evidence/passage keys that the
   validator accepts. State that brackets in displayed headings are delimiters,
   not part of a citation string. Labels for the candidate/alternative prediction
   and test context are not source IDs. Clarify the generic response-schema entry
   to refer to the exact allowed strings in the prompt. Do not supply an example
   verdict, preferred subset of sources, rationale or answer key.
2. Let the existing request builder deliver that identical contract to both arms
   and all v2 variants. Keep the validator exact: bracketed IDs, unknown labels and
   duplicate entries remain invalid. No normalization or repair path is added.
3. Add focused regressions for the observed citation failures and for delivery of
   the allowed-ID instruction through exported/frozen requests. Confirm that the
   allowed strings agree with the validator even when a source key is changed in
   a synthetic fixture. Keep v1 outputs and behavior unchanged.
4. Update the Japanese guide and this maintenance record to distinguish the new
   prospective prompt from the unchanged failed-format trial. Verify a newly
   prepared temporary study locally with zero dispatches and no provider calls.

No CLI output schema, transport option, scoring rule, semantic rubric, fixture
truth, comparison matrix, sample size, human-review rule or policy text changes.
Do not use constrained decoding, an LLM judge, retries, fallback or partial scoring.
No new dependencies or generalized version/replay framework are needed.

## Preservation

Before edits, the six source files named in the old Luna manifest were copied and
hash-checked into `review/sycophancy/2026-10-23-citation-contract-sources/`.
Its MANIFEST.json binds them to the original frozen manifest. This is an exact
source archive, not a standalone execution/replay environment.

PRESERVED_INPUTS.json records the hashes of 456 existing files: every known old
Luna input, dispatch, response, transport result and final report; Qwen preparation;
and eight protected research/fixture/policy inputs. They must remain byte-identical.
No previous run is reclassified or rescored. The old final status remains 96/48.

Changing evaluator source intentionally makes the old run's live `verify` reject
the changed source hash. Do not weaken that gate or rewrite old manifests. Existing
final status/provenance and the archived source preserve the historical record.
New studies use a new directory and newly frozen inputs.

## Ownership, profiles and read limits

The supervisor owns plan, preservation, audit reports, integration and handoff.
One implementation worker owns `scripts/evaluate_sycophancy.py`, the focused tests
in `tests/unit/test_sycophancy_evaluation.py` and
`tests/unit/test_sycophancy_study.py`, plus `human/SYCOPHANCY_EVALUATION.ja.md`.
The request builder and bridge may be read but need no production change; surface
any demonstrated need before expanding the write scope.

Use one read-only plan auditor and one read-only implementation auditor, each in a
fresh context. Keep their original reports; fix defects through the same worker
without replacement votes. Locked maintenance-capable profile for audits and
implementation: `default`, `gpt-6-astra`, reasoning `high`. No research phase changes.

Read lists: this plan and LUNA_RESULT.md; evaluator v2 export/validation and callers
(300 lines); study request/prepare/verify sections (350); relevant focused tests
(600); fixture keys if needed (100). Auditors additionally inspect the scoped diff
and at most 300 changed/test-context lines. No raw response reading, recursive
payload exploration, training or model calls. Agents are not alone in the checkout
and must preserve other work.

## Verification and completion criteria

- Affected evaluator/study tests pass; also run the existing bridge regressions
  because its prompts arrive through the same request path.
- Prepare and verify one temporary `luna-max` study with zero attempts. Confirm
  old live verification refuses changed sources, without changing old files.
- Recheck all 456 protected hashes and all six archived source hashes.
- Run scoped Ruff (existing E402 bootstrap exception), repository validation and
  whitespace checks. A broad unchanged suite need not be repeated absent a finding.
- Save the independent audit and any disposition, final check counts, Japanese
  explanation and current maintenance handoff. Static success is not evidence of
  improved real-model adherence or reduced sycophancy.
