---
name: run-experiment
description: Run an approved locked experiment, or recover interrupted review routing from TRAINED without retraining.
---

# Run Experiment

Speak to the human in Japanese; keep files in English.

1. Read `research/CONTEXT.md`, `research/STATE.json`, the active `MANIFEST.json`, config, and `SCOPE.json`.
2. Require phase `IMPLEMENTED`, `SANITY_PASSED`, or `TRAINED`. Pilot/full also require an accepted implementation audit; do not bypass `review_implementation`.
3. Run `python3 scripts/run_experiment.py --id <ID>` once. Optional config.comparison executes all locked arms/conditions/seeds sequentially under this ID and produces a joint aggregate. No per-run Agent or approval. The script owns checks, budgets, artifacts, hashes, transitions and failures.
4. Report the final status line. On failure, route to `$debug-failure`; do not retry here. Recorded comparison results must not be erased or mixed with repaired code.
5. Stop after the script completes. Evaluation and integrity review are separate phases.

Boundaries:
- Do not invoke training modules directly, alter the locked plan, tune controls, add seeds, or launch background jobs.
- Do not inspect implementation or test source; the deterministic runner owns code loading in this phase.
- Do not inspect checkpoints, batch histories, or raw data.
- Resume only through the same script. `SANITY_PASSED` requires its artifact; `TRAINED` reuses aggregate artifacts and never retrains.
