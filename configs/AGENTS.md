# Configuration scope

- Keep one locked JSON config per experiment. Optional `comparison` defines required arms, conditions and seeds; scripts derive per-run configs.
- Before plan locking, change only fields required by the declared method.
- After locking, do not edit the config; create a new experiment for a scientific change.
- Keep smoke and pilot limits bounded. Full execution requires explicit approval in `research/STATE.json`.
