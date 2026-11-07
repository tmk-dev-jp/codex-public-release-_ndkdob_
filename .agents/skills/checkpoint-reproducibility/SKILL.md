---
name: checkpoint-reproducibility
description: Record reproducible experiment inputs with a minimal scoped Git commit and immutable annotated tag when a checkpoint is requested.
---

Use maintenance routing; do not change experiment phase, locked records, results, or artifact hashes. 

1. List exact input paths and inspect scoped Git changes: code, configuration/locked plan, dependency lock or requirements, and data manifest. Include every changed/new input needed to reproduce. Never inspect raw data or reference payloads.
2. Make one checkpoint before execution, or an explicitly requested result milestone. Reuse unchanged checkpoints. A direct checkpoint request authorizes the selected inputs; otherwise present paths and tag for approval before mutation.
3. From the repository root, select existing regular files individually:

   ```bash
   python3 scripts/reproducibility_checkpoint.py --tag repro/EXP-ID-inputs --path src/dl_research/training/trainer.py --config configs/experiments/EXP-ID.json --dependency pyproject.toml --data-manifest data/MANIFEST.json
   ```

   Repeat options for additional files; include the locked plan through another `--config`. No directory selection, blanket staging, push, tag replacement, or fallback to broad commits. The helper preserves unrelated staging/files, rejects partial staging of selected files and unfinished Git operations, commits only changed selected inputs, and annotates the tag with references and capture limits. On `ERROR`, stop; never clear another writer's index/lock or rewrite tags.
4. Report commit, tag, selected scope, and excluded changes affecting reproduction. Reproduce from an isolated checkout plus recorded dependencies and user-managed data. Do not claim reproducibility when required inputs remain uncommitted or manifests lack stable data identities. Tags do not capture external data, installed environments, secrets, drivers, or runtime determinism.

Refs update together; selected index entries synchronize under Git's index lock. A crash after ref publication can leave an old index: inspect commit/tag and selected paths before retrying. No published refs are rolled back or rewritten. 
