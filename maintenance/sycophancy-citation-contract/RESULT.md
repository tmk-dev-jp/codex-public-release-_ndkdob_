# Citation-format clarification outcome

> Public distribution note: The historical Luna run and Qwen preparation records
> are excluded from this template. Counts and verification statements below
> describe the original maintenance work; the omitted inputs, raw logs and
> frozen manifests cannot be inspected or reverified from this distribution.
> No historical results or hashes were regenerated. See
> [public distribution scope](../../review/sycophancy/PUBLIC_DISTRIBUTION.md).

The user-requested plan and modification are implemented. Production changes are
confined to `export_v2` in `scripts/evaluate_sycophancy.py`: every prompt now lists
all exact bare citation IDs derived from its evidence/passage keys, distinguishes
display brackets and section labels, and points the schema placeholder to that
list. Both guidance arms and all variants share this instruction. No answer key,
preferred citation subset or example verdict was introduced.

Strict validation, scoring, v1, transport, fixtures and policies are unchanged.
Bracketed IDs, unknown section labels and duplicate entries remain invalid.
The Japanese guide explains prospective scope and historical verification limits.

## Independent review

- PLAN_AUDIT.md: PASS, no actionable findings.
- IMPLEMENTATION_AUDIT.md: PASS, no actionable findings.
- Each phase used one fresh, read-only auditor. Original reports are retained;
  there were no replacement votes or repeat audits.
- The implementation worker corrected a synthetic renamed-fixture annotation
  during testing. This affected test setup only, not the real fixture or criteria.
- After the implementation audit, repository validation treated archived `.py`
  copies as active modules and rejected the archived boundary adapter's path.
  The supervisor renamed those four copies to `.py.source` and updated only their
  archive locations in MANIFEST.json. Their bytes and source hashes are unchanged;
  no runtime/test code, original evidence or audit report changed. No repeat audit
  vote was requested for this archive-packaging correction.

## Verification

- Evaluator/study tests: 58 passed in 7.36 seconds.
- Existing Codex bridge regressions: 13 passed in 10.25 seconds.
- Total affected tests: 71 passed. The unchanged broad suite was not repeated.
- Scoped Ruff with the existing E402 exception passed.
- v1 exports before/after are byte-identical.
- A fresh temporary Luna max preparation verifies successfully: 144 planned,
  zero attempts, identical runtime settings and a changed prompt fingerprint.
  No model calls were made. Its path is `<historical-verification-directory>`;
  it is a local verification artifact, not a newly launched comparison.
- The old Luna run verified as 96 valid/48 invalid before edits. After edits the
  live verifier correctly refuses the changed source hash; its gate was not relaxed.
- All 456 protected existing files remain byte-identical, including the old raw
  responses, frozen inputs and final reports, the Qwen preparation, and eight
  protected research/fixture/policy inputs. Qwen still has zero dispatches.
- All six archived source copies match their original manifest hashes. The other
  five current source files also match; only the evaluator changed.
- Final repository validation passed: 3438 files, zero warnings. Whitespace checks
  passed. Post-packaging checks again confirmed all 456 protected files and all six
  archived source contents retained their hashes.

## Interpretation and next boundary

The previous comparison remains unscorable with 96 valid-format and 48 invalid
responses. The change clarifies future inputs; it does not retroactively improve
that result. Model adherence and sycophancy reduction have not been measured under
the revised prompt. No additional inference or human semantic assessment occurred.

New comparisons require a new frozen directory. The exact source archive at
`review/sycophancy/2026-10-23-citation-contract-sources/` is preservation evidence,
not a standalone replay environment. Old manifests must not be rewritten to match
current code. The planned implementation, audits and final checks are complete.
