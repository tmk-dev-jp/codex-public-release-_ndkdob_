---
name: initial-setup
description: Interactively initialize this deep-learning research repository before its first experiment. Use when research/STATE.json has project_status "setup" or the user explicitly requests initial setup. Do not train, search papers, or implement an experiment.
---

# Initial Setup

## Outcome

Collect the minimum decisions required to replace setup placeholders. Keep agent-facing files and reasoning artifacts in English. Speak to the user in Japanese unless requested otherwise. Stop after validation; experiment planning is a separate session.

## Read Boundary

Read only:

- `AGENTS.md`
- `research/GOAL.md`, `STATE.json`, `QUEUE.json`, `CLAIMS.jsonl`
- `data/MANIFEST.example.json`, `data/README.md`
- `configs/templates/smoke.json`, `configs/templates/pilot.json`
- `pyproject.toml`
- `TREE.txt` or a path-only file listing when names must be confirmed

Do not recursively scan `data/`, `artifacts/`, `references/`, or completed experiments. Do not inspect raw samples unless the user identifies a small sample and authorizes reading it.
Do not open Python implementation during setup; defer code mapping to experiment planning.

## Interactive Procedure

1. Report which required values are known, placeholders, or inconsistent.
2. Ask one compact batch of only unanswered questions, at most eight:
   - project ID and decision-relevant research question;
   - task, input, target, and expected shapes;
   - dataset path, source, license, split rule, and leakage prevention;
   - baseline and the first controlled comparison;
   - primary metric, direction, falsifier, and decision mode: a numeric threshold, or an expected trend with minimum observations and weak/conflicting evidence;
   - compute limits, device, seed policy, and deterministic requirement;
   - stop conditions;
   - optional user-supplied references.
3. Distinguish confirmed facts, assumptions, and unresolved items. Never convert partial agreement into confirmation.
4. Show the proposed setup and exact files to edit. Request confirmation once. When choices are delegated, use conservative smoke defaults and label them as assumptions.

## Writes After Confirmation

- Fill `research/GOAL.md`.
- Replace `C-001` in `research/CLAIMS.jsonl`.
- Replace `Q-001` in `research/QUEUE.json`.
- Create `data/MANIFEST.json` from the example. Reference raw-data paths; never copy, rename, or mutate raw data.
- Update `research/STATE.json`: project ID, `project_status: "ready"`, no active experiment, and `next_action.mode: "select_experiment"` for creating the first smoke experiment.
- Add reference records only for papers supplied by the user. Store bibliographic metadata and abstract-level notes by default; do not search, download, OCR, or read full papers.
- Do not change source code unless setup cannot be represented by configuration. Report that case instead.

## Validation

Check that required placeholders are removed, JSON is valid, metric and task agree, split rules and leakage checks are explicit, data availability is accurately stated, and no baseline result is invented. Run:

```bash
python scripts/build_context.py
python scripts/validate.py
```

Do not run training or create an active experiment.

## Final Response

Return one concise Japanese summary containing changed files, assumptions, unresolved items, and the next command:

```bash
python scripts/new_experiment.py --id EXP-001 --stage smoke
```

Then instruct the user to start a new session with `$plan-experiment`.
