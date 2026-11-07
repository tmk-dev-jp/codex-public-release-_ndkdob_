# Hypothesis Policy

Use this file to constrain experiment planning before `$plan-experiment`.

## Hard Bans

- None.

## Soft Discouragements

- Avoid exploratory ablation-first, seed-search, and fine-condition-sweep hypotheses before core evidence. Essential controls that distinguish the main alternative belong in the core comparison.

## Allowed Alternatives

- Prefer a coherent, mechanism-driven method comparison sized to the research decision. Jointly necessary components and related predictions may be tested together; do not attribute their individual effects without controls.
- Use one preregistered seed per run. Group necessary comparisons and repetitions under one core hypothesis using a bounded `comparison` design. Do not select favorable seeds. Smoke establishes readiness, not research support.

## Review Conditions

- Revise this policy only when the user explicitly changes the research scope or approves a new planning constraint.

## Last Updated

- Initial template. No project-specific hard bans have been set.
