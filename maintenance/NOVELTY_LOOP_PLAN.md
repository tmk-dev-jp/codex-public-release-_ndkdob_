# Novelty and Research Question Continuity

## Objective

Improve the research loop so novel, falsifiable contributions remain tied to the
research question throughout planning, implementation, evaluation and direction
updates. The user specifically requires that the loop not forget either the
research question or novelty during ongoing work.

## Observed gaps

- CONTEXT summarizes the goal by a line limit and places active research content
  after operational state and memory. Finalization removes the active hypothesis
  while the digest primarily retains metrics and next actions.
- Decision facts foreground the metric without a compact statement of the
  research question, novelty claim or discriminating evidence.
- Novelty routing accepts a low-risk/proceed label even when the search,
  closest-work comparison and claim are absent. The schema accepts empty lists
  and empty facet comparisons.

## Changes and acceptance criteria

1. Derive a compact Research Focus from existing authoritative GOAL and plan
   fields, without a second editable truth source. Keep it at the start of
   CONTEXT for active work and the named latest completed experiment. Never
   silently truncate this focus to fit memory or digest content.
2. Include the same focus in decision facts, binding it to the facts' input hash.
   A change in question or planned contribution must make existing facts stale;
   conclusion edits must not. Existing locked-plan and goal-audit hashes remain.
3. Require source-linked comparisons, substantive facets, search terms and a
   novelty claim before a novelty record can proceed. Missing compact evidence
   means needs_human/revise, never fabricated sources or proof from no search hits.
4. Make phase guidance connect candidate generation, locked novelty, implementation,
   evaluation and next-step selection to the research question. Metric success
   and a novel contribution remain separate judgments. Preserve bounded search,
   essential controls, independent audits and human approval of goal changes.
5. Verify long-context retention, finalization handoff, facts staleness,
   empty-novelty rejection, source comparison acceptance, and unchanged phase
   boundaries with focused and full regression checks.

## Limits

This work improves persistence and evidence discipline; it cannot prove that a
scientific idea is novel or useful. No research-specific literature search,
training, model evaluation, or modification of accepted results is authorized
or needed for this maintenance change. No added runtime dependencies.

## Completion evidence

| Criterion | Evidence |
|---|---|
| Focus survives long context and experiment completion | `tests/unit/test_research_focus.py` checks active/completed sources, all focus values, 20-line questions and oversized memory/digest |
| Focus cannot silently disappear | Tiny-budget regression requires an explicit error before a context write |
| Question/novelty changes invalidate facts | Decision-facts regressions reject each change and permit conclusion-only edits |
| Novelty requires comparisons | `test_research_memory.py` rejects empty, placeholder, duplicate-source and malformed proceed evidence, while permitting explicit insufficient-evidence review |
| Novelty changes invalidate plan review | `test_plan_audit.py` verifies the source comparison is in the bundle and a later novelty change invalidates acceptance |
| Scientific purpose persists across phases | `automation/RESEARCH_FOCUS.md`, phase skills, experiment template and `human/NOVELTY_LOOP.ja.md` specify question/novelty/evidence checks and separate score gains from contribution |

Final commands and results are recorded in `maintenance/HANDOFF.md`. The live
project remains in setup; only its generated context was refreshed.
