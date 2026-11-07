---
name: update-research-direction
description: Update direction and add hypothesis candidates after result review; preserve baselines.
---

# Update Research Direction

Use after result review. Follow `automation/RESEARCH_FOCUS.md`.

## Inputs

1. Read context, state, goal, claims, evidence, queue, decisions, proposed method, digest, hypothesis policy, idea bank and compact memory.
2. Read the latest completed record only if its needed result is absent from the digest. No raw data, unnamed artifacts, checkpoints, full papers or code.

## Procedure

1. Classify the locked result: threshold met/missed or expected/opposite/mixed/uninformative trend. Use locked aggregates, not post-hoc metrics/patterns; separate observation from interpretation.
2. Update `research/PROPOSED_METHOD.md`: question, novelty evidence/status, covered/missing GOAL evidence and next gap. Smoke supports readiness only. Limit claims to observed evidence.
3. Check for a result-derived hypothesis even with a nonempty queue. Reuse matching ideas; reject replays, dead ends, policy conflicts, grids and seed searches. If defensible, append at most one `candidate` to `research/ideas/IDEA_BANK.jsonl` using the fields in `$select-research-branch`. Cite experiment/evidence IDs in `source_refs`; label the mechanism as untested inference and give its falsifier in `next_test`. Otherwise record why none was added in DECISIONS. No external search is implied.
4. Update claims, queue and decisions. Queue at most one adequate next experiment; do not abandon necessary study coverage just to avoid cost. Uninformative results need a remedy and budget. Link the selected queue item through `idea_id`; preserve other items/history. Storage alone does not queue a run. Respect stop/defer. Research-goal changes need human agreement.
5. If none is justified, record stop/defer; never invent work.
6. Preserve baseline records and `STATE.baseline_experiment`.
7. Run `python3 scripts/complete_direction_update.py`, then `python3 scripts/validate.py`.

## Boundaries

- No experiment creation, approval, execution or code planning. Use `$select-next-experiment` next; normal novelty and plan audits apply.
