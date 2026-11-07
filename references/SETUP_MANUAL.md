# Initial Setup Manual

Use this manual only with `$initial-setup`.

## Dialogue

Ask at most eight questions in one batch:

- Research goal and decision to support.
- User-supplied baseline source: paper, GitHub repository, or web article.
- Approved reading scope: exact section, page, figure, table, URL, or repository file.
- Dataset manifest or data location managed by the user.
- Primary metric, direction, and decision mode: a minimum useful effect, or a preregistered trend with minimum observations and weak or conflicting evidence.
- Compute budget for smoke and pilot.
- First smoke objective.

If the user marks an item as undecided, provide a short discussion path instead
of forcing a value:

- State why the item is needed and whether it blocks setup, planning, or only
  baseline registration.
- Offer two or three conservative choices plus an explicit `defer` option.
- If the user delegates the choice, record the selected default as an
  assumption.
- If the user defers a blocking item, keep `research/STATE.json` in `setup`,
  record the item as unresolved, and set the next queue objective to resolve it.
- If the user defers a non-blocking item, proceed only with the confirmed
  subset and keep the deferred item out of locked claims, baselines, and data
  facts.

Before editing files, summarize confirmed facts, assumptions, unresolved items,
and the exact files to update. Request one confirmation for that proposal.

## Mapping

- Write confirmed research intent to `research/GOAL.md`.
- Write the first queue item to `research/QUEUE.json`.
- Keep `research/STATE.json` in `ready` unless setup is still incomplete.
- Record data facts in `data/MANIFEST.json`.
- Register source metadata in `references/records/` and baseline metadata in `baselines/`.

## Boundaries

- Do not infer the image task before reading an approved source scope.
- Do not read full papers, whole repositories, or broad web pages.
- Do not open Python implementation during setup; use path names only and defer code mapping to planning.
- Do not implement code, create an active experiment, or run training.
- Label defaults as assumptions and unresolved items as unresolved.
