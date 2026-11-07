---
name: monitor-experiment
description: Check an active run's artifacts and phase mechanically when execution status is needed.
---

# Monitor Experiment

Speak to the human in Japanese.

1. Read `research/CONTEXT.md` and `research/STATE.json`.
2. Confirm there is one active experiment and do not read broad artifacts.
3. Run `python scripts/monitor_experiment.py --id <ID>`.
4. If status is `completed`, route to `$evaluate-experiment` or `$review-experiment-result` according to phase.
5. If status is `failed`, route to `$debug-failure`.
6. If status is `not-started`, `running-or-prepared`, or `sanity-passed`, report the compact status and stop.

Boundaries:
- Do not train, debug, evaluate, or interpret results here.
- Do not inspect checkpoints or write reports.
- Do not start background monitoring loops unless a human explicitly asks.
