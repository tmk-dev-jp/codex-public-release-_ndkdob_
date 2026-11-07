---
name: replenish-research-hypotheses
description: Investigate gaps and replenish an exhausted hypothesis queue before target creation in an explicitly authorized unattended loop, or on direct request.
---

# Replenish Research Hypotheses

Speak Japanese; keep files in English. Use within a requested unattended/agent-led loop or on direct request; this grants no loop authority.

1. Require no active experiment and `next_action.mode=select_experiment`. Read context, state, GOAL, queue, proposed method, hypothesis policy, idea bank, digest and compact memory. List paths first; read only relevant compact reference/baseline records. No Python source or completed experiment records.
2. Reuse a viable untested idea first. Otherwise investigate one missing evidence question from GOAL. Query the existing paper graph once via `pk.py brief` if available. Within approved scope inspect at most 2-3 similar titles/abstracts/snippets. Unattended invocation authorizes this goal-scoped search; broader research, downloads, OCR and full papers need separate authority.
3. Record question, closest-work gap and rival predictions in `research/DECISIONS.md`. Follow `automation/RESEARCH_FOCUS.md` and its contribution contract: separate source facts from inference and state meaningful progress. Exclude dead ends, policy conflicts, replays, seed searches and grids. Respect stop decisions, goal completion and exhausted budgets; do not manufacture work.
4. Select one falsifiable comparison sufficient for GOAL, with essential controls. Write its expanded idea as `candidate`. Add a fresh queue ID with `status=ready`, `idea_id`, title, hypothesis, falsifier, minimal_test, primary_metric, baseline_id, claim_ids and priority/cost/risk fields. No confirmation is needed in the authorized loop. Preserve history; explain selection.
5. If none is defensible, record the blocking gap and leave the queue exhausted. Run `python3 scripts/validate.py`. Return to the invoking router: it creates one target or blocks without repeating investigation.

Do not edit GOAL, state, baselines, accepted evidence or code, or create, approve, implement or run experiments. Normal novelty and plan audits still apply.
