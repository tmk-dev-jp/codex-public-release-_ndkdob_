---
name: prepare-data-manifest
description: Describe user-managed datasets and splits in data/MANIFEST.json when preparing or reviewing data setup.
---

# Prepare Data Manifest

Use this before planning any experiment that depends on user data. The manifest records compact facts; raw samples remain user-managed.

## Read

- `research/CONTEXT.md`
- `data/README.md`
- `data/MANIFEST.example.json`
- `data/MANIFEST.json` if it exists
- Exact metadata or sample files only when the user names them and authorizes reading them

## Procedure

1. Classify each manifest field as confirmed, assumed, placeholder, or unresolved.
2. Ask for missing high-impact facts in one compact batch: dataset path, source, license, task, input shape and dtype, target shape, split counts, split rule, content or split hash, and leakage checks.
3. When the user delegates defaults, use conservative placeholders and label them as assumptions.
4. Update only `data/MANIFEST.json` from confirmed facts and explicit assumptions. Never copy, rename, delete, or inspect raw data recursively.
5. If source code changes are needed for a new DataLoader, stop and route that work to `$implement-experiment` after planning.
6. After edits, run `python3 scripts/build_context.py` and `python3 scripts/validate.py`.

## Boundaries

- Do not download datasets or call training code.
- Do not infer a task from file names alone.
- Do not mix split changes with model-comparison experiments.
- Do not place Japanese text outside `human/`.
