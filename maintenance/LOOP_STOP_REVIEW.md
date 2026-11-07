# Autonomous Loop Stop Review

## Findings and changes

| Observed stop | Cause | Change |
|---|---|---|
| A newly locked plan stops at missing novelty | The router treated an unperformed prerequisite as a human judgment | Route once to the bounded novelty skill before plan audit, then recheck its evidence |
| An audit/preparation completes without changing the phase | The ordinary loop required a STATE advance even though builders, compression and audits may only write evidence or change gate action | Count changed evidence and gate actions as progress; unchanged observations alone remain no progress |
| Full-stage implementation, review or trained recovery stops for compute approval | The unattended router applied training authorization to every nonplanning operation | Require matching full approval at execution entry; allow approved implementation and review preparation, and existing-result processing |

The ordinary router also checks full approval before invoking the runner, so a
missing approval is reported as a decision gate rather than an execution error.
Both routers use the same rule. The runner's own compute policy stays enforced.

## Deliberate stops retained

- Ordinary plan decisions and operation/three-phase boundaries; only an explicit
  unattended request can span an experiment.
- Explicit unattended authorization, target mismatches and one-experiment limit.
- High-risk, rejected, incomplete or human-pending novelty; unavailable or
  insufficient evidence is not converted into a pass.
- Failed audits, changed locked inputs, stale provenance, ambiguous scientific
  output, unavailable reviewers and required human interpretation.
- Missing data decisions, expanded literature scope and execution failures.
- No demonstrated progress after a correction. Training is never retried here.

## Acceptance evidence

Regression tests exercise missing-novelty preparation followed by a real evidence
record, substantive novelty blocks, full preparation and trained recovery without
compute approval, missing/wrong-ID approval at execution, and matching approval.
Skill guidance, both ordinary startup prompts and Japanese instructions reconcile
preparation progress with the existing presentation recovery policy. No research
experiment is run as part of this maintenance work.

- Focused router tests: 64 passed.
- Unit/smoke suite: 432 passed, 2 sandbox integration cases deselected, 13 subtests
  passed. Those sandbox cases are outside the changed routing surface.
- Repository validation: zero warnings; skill and instruction budgets pass.
- Changed runtime/test files pass Ruff; tracked changes pass `git diff --check`.

These checks cover deterministic routing and instruction consistency, not a live
agent's autonomous scientific judgment.
