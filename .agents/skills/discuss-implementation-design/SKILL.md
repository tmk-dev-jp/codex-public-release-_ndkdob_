---
name: discuss-implementation-design
description: Discuss experiment design when consultation is requested or an unresolved scientific choice needs a decision.
---

# Discuss Implementation Design

Speak to the human in Japanese; keep agent-facing edits in English.

1. Read context and the relevant design or active plan. Add state, goal, policy, or a named baseline record only when the unresolved choice depends on it.
2. Use path listings first. Before implementation, open only Python predeclared in budgeted `planning_reads`; choose implementation startup files from paths, not broad source inspection.
3. Relate the unresolved choice to GOAL's evidence strategy: adequate comparisons, observations and budget, not just the smallest implementation.
4. Use existing decisions and authorization. Routine details preserving the locked design belong in `$implement-experiment` and need no separate discussion.
5. Present only decision-relevant alternatives in Japanese, with research effect, implementation risk, and a recommendation.
6. Keep proposed method separate from baseline. Do not update baseline to match a new method.
7. Keep jointly necessary method components and discriminating controls together. Avoid exploratory ablations, favorable-seed searches and micro-grids; do not confuse a single executable run with the whole study.
8. After decisions, summarize confirmed design, assumptions, unresolved items, exact files, the smallest reasoned `implementation_entry_reads` set, and validation checks.

State rules:
- No active experiment: discuss proposed-method design only; with explicit confirmation, update `research/PROPOSED_METHOD.md`.
- `DRAFT`: edit only active `EXPERIMENT.md`, config, and `SCOPE.json` fields needed.
- `PLANNED`: do not edit locked files. Requested science/scope revisions use `$revise-experiment-plan`; otherwise use `$implement-experiment` when approval is recorded.
- `IMPLEMENTED` or later: route new ideas to `$select-next-experiment` or `$update-research-direction`.
- `FAILED`: use `$debug-failure`.

Do not implement, debug, train, evaluate, hash artifacts, approve plans, widen scope silently, inspect broad sources, or change baseline records.
