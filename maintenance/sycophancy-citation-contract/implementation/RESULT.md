Implemented the four owned files:

- `export_v2` now lists every allowed bare evidence/passage key, explains display brackets and section labels, and clarifies the schema placeholder.
- Tests cover dynamic source renaming, all variants, bare-ID acceptance, bracketed/section-label/duplicate rejection, and matching frozen A/B payloads.
- Japanese guide documents prospective scope, unchanged 96/48 history, historical code requirements, archive limitations, and no efficacy claim.

Verification:

- Evaluator/study tests: **58 passed in 7.36s**.
- Scoped Ruff with `--ignore E402`: passed.
- Scoped `git diff --check`: passed.
- Baseline diff confirms production changes are confined to `export_v2`; validator, scoring, v1, study and bridge remain unchanged.

Initial tests exposed a missing annotation update in the synthetic renamed fixture; corrected before the successful rerun. No model calls, raw historical response reads, or old-run writes. No blockers. Bridge regressions, preservation checks and integration audit remain with the supervisor.
