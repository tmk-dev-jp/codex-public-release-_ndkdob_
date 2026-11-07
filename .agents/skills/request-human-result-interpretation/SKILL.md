---
name: request-human-result-interpretation
description: Prepare result files or accept a human interpretation when metrics alone cannot support a reliable decision.
---

# Request Human Result Interpretation

Use this after deterministic execution, before finalization, when result interpretation needs human judgment.

## Prepare Files

1. Read `research/CONTEXT.md` and `research/STATE.json`.
2. Confirm the active phase is `READY_TO_FINALIZE`, `REVIEW_REQUIRED`, or `TRAINED`.
3. Run `python3 scripts/build_human_result_packet.py --id <ID>`.
4. Tell the user to inspect `human/results/<ID>/RESULTS.md`, including the machine-generated decision facts, and fill `human/results/<ID>/INTERPRETATION.md`.

## Accept Interpretation

After the human fills the file:

1. Run `python3 scripts/accept_human_interpretation.py --id <ID>`.
2. Confirm the experiment is `READY_TO_FINALIZE`.
3. Stop before finalization unless the user explicitly asks to finalize.

## Boundaries

- Do not infer the human interpretation from metrics when the user requested human judgment.
- Do not inspect checkpoints, batch histories, raw data, full papers, or implementation files.
- Copy `Mechanical rule status` exactly from `DECISION_FACTS.json`; acceptance rejects a different value.
- Judge only the locked threshold or preregistered trend rule. Do not create a post-hoc trend from the visible results.
- Do not change locked metrics, decision mode or criterion, baselines, seed policy, split, or success rules.
- Keep Japanese free-form interpretation under `human/results/<ID>/INTERPRETATION.md`; only English required fields are copied into `EXPERIMENT.md`.
- Keep copied `Conclusion` and `Issues and Next Direction` within the configured 400-word combined limit.
