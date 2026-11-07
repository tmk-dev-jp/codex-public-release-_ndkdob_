---
name: configure-hypothesis-policy
description: Record user-requested exclusions for future experiment hypotheses.
---

# Configure Hypothesis Policy

Use this before `$plan-experiment` when the user wants to prohibit specific hypothesis directions.

## Inputs

1. Read `research/CONTEXT.md`, `research/GOAL.md`, and `research/planning/HYPOTHESIS_POLICY.md`.
2. Ask only for missing policy decisions needed to make the ban actionable:
   forbidden idea, reason, scope, allowed alternatives, expiry or revision condition.
3. Separate hard bans from soft discouragements. Hard bans must block planning; soft discouragements require a written justification if used.

## Update

Edit only `research/planning/HYPOTHESIS_POLICY.md` unless the user explicitly asks for documentation updates.

Record:

- Forbidden hypotheses: ideas, mechanisms, comparisons, datasets, model families, or experiment styles that must not be proposed.
- Rationale: scientific, ethical, resource, novelty, leakage, or scope reason.
- Allowed alternatives: directions that remain acceptable.
- Review condition: when the ban may be revised or removed.
- Last updated note: compact human decision summary.

## Boundaries

- Do not create an active experiment, plan an experiment, inspect implementation files, search references, or run training.
- Do not encode vague dislikes as hard bans. Make each hard ban testable enough for `$plan-experiment` to apply.
- Keep agent-facing content in English.
- Run `python3 scripts/build_context.py` and `python3 scripts/validate.py` after edits.
