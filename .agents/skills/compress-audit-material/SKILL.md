---
name: compress-audit-material
description: Compress oversized audit inputs or unaccepted reports within the current phase, preserving evidence, verdicts and configured limits.
---

# Compress Audit Material

Use on an audit gate's `compress` action or a size-only rejection. This is subordinate preparation in the current phase, not a new audit, extra phase or unattended-loop authorization.

1. Run `python3 scripts/compress_audit_material.py --id <ID> --task <plan-audit|implementation-audit|integrity-audit>`. It packs current JSON losslessly and removes blank formatting or identical fields. Plan builders try packing automatically before rejecting oversized input.
2. On `status=ready`, rerun the same audit gate and continue its action in this turn. No user approval or extra Agent is needed for presentation-only compression.
3. On `status=needs-edit`, read only affected fields in the candidate and sibling ORIGINAL.md. Remove repetitions in CANDIDATE.md, retaining each field's unique vocabulary and every finding, caveat, condition, negation, identifier and number. Do not add judgment, soften fail/warn, hide gaming or drop uncertainty. Keep other prose unchanged. Never edit the original, locked records or accepted audits.
4. Run the command with `--apply`. It checks hashes, fields, verdict, vocabulary, numbers/paths/quoted identifiers, qualifications and limits. These checks do not prove equivalent meaning: confirm it against ORIGINAL.md first. Then rerun the gate and acceptor, not the auditor. The archive stays outside the bundle.
5. Continue the enclosing loop only after validation succeeds. An improved artifact or gate action counts as progress without a phase transition. No replacement reviewer, execution retry or unbounded correction cycle.

On irreducible essential input, changed provenance, missing/ambiguous assessment, or a correction that still makes no progress, stop with that substantive reason. Never raise limits, delete evidence or rewrite the scientific plan to fit.
