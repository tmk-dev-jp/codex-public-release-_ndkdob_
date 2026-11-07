---
name: scan-research-landscape
description: Map research gaps from scoped sources when the user requests a broader literature landscape scan.
---

# Scan Research Landscape

Speak to the human in Japanese; keep files in English.

1. Read `research/CONTEXT.md`, `research/GOAL.md`, `references/records/`, `baselines/INDEX.json`, exact baseline records, `research/ideas/IDEA_BANK.jsonl`, and `research/memory/OPEN_QUESTIONS.md`.
2. Do not read `references/originals/`, `references/inbox/`, raw data, completed experiment folders, or broad repos. Web search needs explicit human permission; use titles, abstracts, READMEs, or snippets only.
3. Run `python scripts/suggest_novelty_axes.py` and use it only as compact metadata, not as proof of novelty.
4. Produce a map with exactly these sections: `known_mechanisms`, `reported_limitations`, `under_tested_conditions`, `negative_space`, `candidate_gaps`.
5. Candidate gaps need `novelty_axis`, mechanism, difference from baseline, contribution to GOAL, and a sufficient next test with essential controls. Do not choose a tiny test merely for low cost.
6. Add/update `research/ideas/IDEA_BANK.jsonl` only after human confirmation, using the expanded idea schema.

Boundaries: do not create experiments, edit source, train, evaluate, update baselines, paste full papers, or select ablations before a core hypothesis exists.
