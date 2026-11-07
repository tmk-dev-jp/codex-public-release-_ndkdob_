---
name: register-source-baseline
description: Register user-supplied sources as compact baseline records before experiment planning.
---

# Register Source Baseline

Use this for baseline provenance and approved reading scope. Prefer script-owned registration over hand-written JSON.

## Read

- `research/CONTEXT.md`
- `references/INDEX.json`
- `baselines/INDEX.json`
- `baselines/templates/BASELINE.json`
- `references/templates/REFERENCE.md` only when creating a compact reference record
- Exact user-approved source excerpts or files only when named by the user

## Procedure

1. Confirm source type: `paper`, `github`, or `web`.
2. Confirm baseline ID, title, reference ID or URL or local path, approved reading scope, planned `src/` implementation paths, primary metric, and dataset assumption.
3. If source metadata is incomplete, ask only for missing registration fields. Do not search or download by default.
4. For user-supplied references, create or update compact records under `references/records/` and `references/INDEX.json` only from approved metadata or excerpts.
5. Register the baseline with `python3 scripts/register_baseline.py ...`; do not manually bypass script validation.
6. Run `python3 scripts/build_context.py` and `python3 scripts/validate.py`.

## Boundaries

- Do not read full papers, whole repositories, broad websites, or raw datasets unless the user explicitly expands scope.
- Do not copy external source trees into this repository.
- Do not invent baseline results, weights, implementation details, or performance numbers.
- Do not edit research goals or experiment plans except to report the registered baseline ID for later use.
