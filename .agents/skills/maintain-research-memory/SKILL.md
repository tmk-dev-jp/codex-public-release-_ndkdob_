---
name: maintain-research-memory
description: Record durable findings and unresolved questions after experiment evaluation or human interpretation.
---

# Maintain Research Memory

Speak to the human in Japanese; keep files in English.

1. Read context, digest, compact memory, idea bank, evidence and experiment ledgers, and the latest finalized or interpreted experiment record.
2. Use the accepted interpretation named by the completed manifest evaluation record. Preserve its human or agent source; an unaccepted human template is not evidence.
3. Append one `research/EVIDENCE.jsonl` record with IDs, decision, locked-rule assessment, primary result, claim scope, integrity verdict, and record/metrics paths.
4. Append one compact ledger record with ID, stage, core change, metric, decision, locked-rule assessment, interpretation source and next action. Keep human_interpretation empty when no human interpretation was accepted.
5. Follow `automation/RESEARCH_FOCUS.md`: retain the question, novelty claim, closest-work IDs and evidence status in durable memory:
   - `INSIGHTS.md` for reusable evidence.
   - `DEAD_ENDS.md` for rejected mechanisms or repeated failures.
   - `OPEN_QUESTIONS.md` for unresolved decisions.
   - `IDEA_BANK.jsonl` statuses for candidates affected by the result.
6. Run `python3 scripts/complete_memory_update.py`. It verifies both ledger entries, activates the evidence ID, advances to direction review, and rebuilds context.

Boundaries:
- Do not update baseline records or raw results.
- Do not invent stronger conclusions than the experiment supports.
- Do not plan, implement, debug, train, or evaluate here.
