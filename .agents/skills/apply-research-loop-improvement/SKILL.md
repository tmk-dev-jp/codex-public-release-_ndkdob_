---
name: apply-research-loop-improvement
description: Implement requested research-template improvements or approved review findings, including focused verification.
---

# Apply Research Loop Improvement

Complete the requested maintenance change, relevant checks, and repairs caused by the change. Speak to the human in Japanese; keep files in English outside `human/`.

## Scope and authority

- A direct template-improvement request or an approved finding authorizes scoped edits and local validation. Do not ask again for that work. Review-only requests do not authorize edits.
- Group related fixes needed for the outcome. Research turn/phase limits do not apply to template maintenance.
- For a session handoff or resumption, use `$handoff-maintenance`; check its snapshot before reopening implementation. Do not create a handoff on every minor edit.
- Read affected files only. Inspect state when the change touches live research contracts; request a decision if it could invalidate an active experiment's locked plan or evidence.
- Preserve script-owned transitions, one-line CLI output, no automatic retries/logs, one active experiment, independent audits, and explicit-only unattended execution.

## Verification and completion

- Skills: validate frontmatter and relevant references; check realistic triggering, approval, and completion cases. Documentation-only edits do not require training or a full model test suite.
- Runtime changes: run affected tests; add coverage for meaningful routing, schema, phase, or gate regressions.
- Run `python3 scripts/validate.py`. Rebuild context only when its inputs changed. Fix patch-caused failures and rerun affected checks; repeat unchanged passing checks only for a concrete new concern.
- Report changes, checks, and limitations. Static validation is not behavioral model evaluation.

Never alter raw data, metrics, checkpoints, completed experiments, or accepted evidence to make validation pass.
