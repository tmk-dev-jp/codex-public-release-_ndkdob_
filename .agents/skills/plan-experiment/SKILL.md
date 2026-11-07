---
name: plan-experiment
description: Plan a goal-sized, falsifiable research comparison and lock its next executable experiment.
---

1. Run `python3 scripts/next_agent_action.py --task planning --id <ID>`. Delegate only on `delegate agent=research_planner`; stop on any other action or error.
2. Use one fresh planner with context, state, goal, controls, policy, compact idea/novelty records, digest, active plan files, named baseline, and optionally one paper-graph brief. No broad reading.
3. Follow `automation/RESEARCH_FOCUS.md` and its contribution contract: map source observations/inference, substantive advance and rival predictions into plan fields. Plan adequate comparisons before minimizing cost; one hypothesis may need multiple runs.
4. Record Research objective, Study role, Evidence coverage (this run versus necessary later runs and their triggers), and Scale justification. Smoke is feasibility only. One coherent method can contain jointly necessary components and related predictions; use matched controls without claiming component-wise effects.
5. Lock one primary metric and at most one diagnostic-only, non-promotion guardrail for a named gaming path. Use threshold only with a meaningful boundary; otherwise preregister a trend, minimum observations, and weak/mixed/opposite/uninformative outcomes.
6. Choose the least costly safe profile: mechanical for no scientific change; balanced for stable work within three write paths; frontier for loss, splits, sampling, metrics, checkpoints, runner, reproducibility, source-porting, ambiguity, or broader changes.
7. List paths first. Budget planning_reads and implementation_entry_reads. Declare every write/test path in change_targets with action, role, and exact symbols.
8. Fill Hypothesis + Method within 700 words, including baseline/candidate behavior, intervention points and invariants. For grouped comparisons, read [comparison contract](references/COMPARISON.md) and use config.comparison. Preserve controls; no exploratory grids or favorable-seed search.
9. Run `python3 scripts/lock_plan.py --id <ID>`; stop for `$audit-experiment-plan`. Do not self-audit, implement, train, retry, or launch another planner.
