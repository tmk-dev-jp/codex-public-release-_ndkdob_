---
name: audit-novelty
description: Assess a candidate contribution to the research question against closest known work.
---

# Audit Novelty

Speak to the human in Japanese; keep files in English.

1. Read context, goal, hypothesis policy, idea bank, novelty checks, reference and baseline records, digest, and the active record. If the paper graph is non-empty, run one focused `pk.py brief` query and use matched node IDs as advisory prior-work cues.
2. Planning-only search exception: obvious keywords only, titles/abstracts/snippets only, 2-3 highly similar hits max.
3. Link the question to the proposed contribution and a discriminating prediction; compare facets, not names. No hits or a better metric alone does not establish novelty.
4. Record one JSONL entry with `experiment_id`, `idea_id`, `query_terms`, `similar_items`, `facet_comparison`, `novelty_claim`, `risk`, `decision`, and `human_review_needed`. For proceed, use 2-3 distinct similar_items objects with `source`, `shared`, `difference`. Fill facets `mechanism`, `condition`, `data_regime`, `objective`, `implementation_change`. Add `contribution` using [the contract](../../../automation/SCIENTIFIC_CONTRIBUTION.md); source observations, inferred advance and rival predictions must be explicit. No placeholders.
5. Use `risk=high` or `risk=block` for near replays, known negative results, or policy conflicts. These must not use `decision=proceed`.
6. Use `decision=needs_human` when compact evidence is insufficient or judgment-heavy; never fabricate sources. Run `python3 scripts/validate.py`. Carry source IDs and the falsifiable difference into the plan Novelty check.

Boundaries: do not download papers, read full papers, inspect broad repos, train, update baselines, or update proposed method records.
