---
name: initial-setup
description: Initialize research goals and project records before the first experiment when research setup is requested.
---

# Initial Setup

Read `references/SETUP_MANUAL.md` and follow it exactly. Use this setup path for template copies and first-project initialization.

## Boundaries

- Keep agent-facing files and working notes in English.
- Speak to the user in Japanese unless requested otherwise.
- Read only the files listed in the manual; do not recursively scan large directories.
- Ask only for missing decisions, in one compact batch of at most eight questions.
- When the user says an item is undecided, use the manual's discussion path:
  explain the blocker, offer conservative choices plus defer, and proceed only
  with confirmed facts or clearly labeled assumptions.
- Separate confirmed facts, assumptions, and unresolved items.
- Show the proposed values and exact edits, then request confirmation once.
- After confirmation, update only goal, claim, queue, data manifest, state, user-supplied reference records, and compact baseline records.
- Do not mutate raw data, invent baseline results, search or download papers, change research code, create an active experiment, or run training.
- Use conservative smoke defaults only when the user delegates a choice; label every such choice as an assumption.
- Do not choose an image task globally. Derive task, metric, and model obligations only from user-approved paper, repository, or web-article scope.
- Register baseline sources with `python scripts/register_baseline.py ...` when enough source metadata and approved reading scope are known.

## Completion

Run:

```bash
python scripts/build_context.py
python scripts/validate.py
```

Return a concise Japanese summary of changed files, assumptions, unresolved items, registered baseline IDs, and the next command. Stop before experiment planning.
