---
name: define-research-intent
description: Record an agreed research goal, initial claim, and first queue item during project setup.
---

# Define Research Intent

Use this after environment and data facts are known. Define the complete study's evidence strategy before its first readiness check; do not create an experiment.

## Read

- `research/CONTEXT.md`
- `research/GOAL.md`
- `research/CLAIMS.jsonl`
- `research/QUEUE.json`
- `research/STATE.json`
- `data/MANIFEST.json`
- `baselines/INDEX.json`

## Procedure

1. Identify placeholders, contradictions, and unresolved decisions.
2. Ask once for missing decisions: project ID, question, evidence-driven action, scope, metric/direction, decision mode and criterion, baseline, robustness, compute limit, strongest alternative explanation, minimum discriminating evidence, falsifier, stop rule, and first smoke objective. Offer `threshold` with a minimum effect, or `trend` with an expected pattern, minimum observations, and weak/conflicting evidence when no defensible numeric boundary exists.
3. Propose GOAL's Evidence Strategy: target claim, essential comparisons and conditions, staged coverage and budget fit. Distinguish readiness from research support. Show values and files before editing.
4. Update only `research/GOAL.md`, `research/CLAIMS.jsonl`, `research/QUEUE.json`, and `research/STATE.json` after confirmation.
5. Set `project_status` to `ready` only when the first smoke experiment can be planned without inventing required facts. Otherwise keep `setup` and record unresolved items.
6. Set `next_action.mode` to `select_experiment` only when ready; otherwise keep `initial_setup`.
7. Run `python3 scripts/build_context.py` and `python3 scripts/validate.py`.

## Boundaries

- Do not register baselines here unless the user also invokes `$register-source-baseline`.
- Do not create `experiments/active/*` or run `scripts/new_experiment.py`.
- Do not inspect papers, repositories, broad web pages, raw data directories, or implementation files.
