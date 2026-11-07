# Presentation Recovery Within a Phase

When a phase is otherwise authorized, correct a presentation error and continue the same phase. This is local document/command preparation, not a new experiment or review.

## Recover without asking

- The record parser accepts heading levels/case/numbering, list markers, bold labels/values, colon spacing and line endings. Run the existing gate or acceptor on the existing output; do not launch another reviewer for those differences.
- Fix a label typo or misplaced existing text only when its intended field and value are unambiguous. Preserve the reviewer's verdict, findings, caveats and recommendations. Never fill a missing scientific assessment with a guess or a default such as pass, none or inconclusive.
- Correct serialization syntax only in not-yet-locked generated inputs with already established values. Never manually rewrite research state, metrics, locked JSON, or accepted evidence to make a validator pass.
- For audit material over its word/character budget, use `$compress-audit-material` as subordinate preparation in this phase. Plan builders try lossless JSON packing first; the audit gate returns `compress` instead of delegating/accepting oversized material. Compress without user intervention, rerun that gate and continue its original action. This consumes no extra phase or Agent.
- For an unaccepted audit report, the compression script retains ORIGINAL.md outside the bundle and prepares CANDIDATE.md when wording must shrink. Remove repeated wording, retaining unique field vocabulary, findings, caveats and conditions; apply through the script, not by editing the original. Mechanical checks do not prove equivalent meaning. No second auditor or changed verdict is authorized. Other unlocked generated documents may also lose redundant phrasing, never evidence or judgments. Keep all configured limits.
- Correct a command spelling, required argument, or output path within the already approved scope when execution has not begun. Reissue only that rejected preparation/acceptance command. Verify the phase and existing artifacts first; never rerun training or overwrite an accepted audit to fix its presentation.

## Verify and continue

Rerun the same gate/validator. Continue only after it succeeds. A corrected output or a changed gate action is progress even if the phase has not advanced yet; this consumes no additional phase or subagent. If the same error survives the correction or no progress can be demonstrated, stop with the exact unresolved issue. Do not reset the loop target or approvals, rebuild reviewed inputs to hide stale hashes, or create an unbounded retry loop.

Compare substantive evidence content and gate actions, not only STATE phase or
file timestamps. A routed first novelty audit is prerequisite work and counts as
one phase; preparation inside an audit (build/pack/accept) remains in that phase.
If novelty preparation produces no record or still lacks evidence, stop instead
of repeating searches. Never treat an unchanged polling response as progress.

## Keep substantive stops

Ambiguous/contradictory values, missing research evidence, changed locked plan/config/scope, stale provenance, failed scientific audits, execution failures, missing data decisions, resource approval, and required human interpretation still stop the loop. Formatting recovery does not permit a second reviewer, self-review, invented facts, altered metrics, or another experiment.
