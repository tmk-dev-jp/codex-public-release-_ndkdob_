---
name: select-next-experiment
description: Create the next active experiment when next_action.mode is select_experiment.
---

# Select Next Experiment

Use after finalization or an explicitly aborted comparison when the next action is selecting an experiment. Aborted results are not scientific evidence; require a concrete remedy before replanning and use a new ID with fresh approval.

## Inputs

1. Read `research/CONTEXT.md`, `research/STATE.json`, `research/GOAL.md`, `research/QUEUE.json`, `research/PROPOSED_METHOD.md`, `experiments/DIGEST.md`, and `experiments/INDEX.json`.
2. Read the latest completed experiment record only when `research/CONTEXT.md` names it and the digest is insufficient.
3. Do not read completed experiments recursively, raw data, artifacts, checkpoints, papers, or implementation files.
4. For paths, inspect `TREE.txt` or a path-only `rg --files` result; do not open `.py` content.

## Procedure

1. Confirm there is no active experiment.
2. First require a material contribution to GOAL's evidence strategy with adequate scope; then rank by decision impact/information gain, compute cost and risk. Do not prefer a tiny cheap test that cannot inform the research decision.
3. Target the next missing evidence for the proposed method, not a baseline update. Match the stage to the evidence needed; do not repeat smoke for already verified execution paths. One active experiment does not mean one experiment for the entire study.
4. If no item is ready, return to the unattended router in `$run-one-unattended-loop`; otherwise ask for `$update-research-direction`. Do not invent facts.
5. If one item is ready, create exactly one experiment with `python3 scripts/new_experiment.py --id <ID> --stage <stage> --queue-id <QID>` and include `--baseline-id` only when the queued comparison already names a registered baseline.
6. Stop after the new experiment is in `DRAFT`.

## Boundaries

- Do not update `baseline_experiment`, baseline records, or baseline indexes.
- Do not plan, implement, train, evaluate, or populate `planning_reads` for the new experiment.
- Do not invent missing queue facts. Route unresolved direction changes to `$update-research-direction`.
