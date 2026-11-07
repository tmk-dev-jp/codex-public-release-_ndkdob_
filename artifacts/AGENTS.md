# Artifact scope

- Read aggregate `metrics.json`, `manifest.json`, and failure-only `error.json` by exact experiment ID.
- Do not inspect checkpoints unless a specific recovery task requires one.
- Do not create histories, batch outputs, epoch logs, tensor dumps, or a `logs/` directory.
- Results are generated artifacts; do not edit them by hand.
