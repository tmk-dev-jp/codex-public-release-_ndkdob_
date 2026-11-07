---
name: select-research-branch
description: Choose a hypothesis-driven research direction when no experiment is active and branch selection is needed.
---

# Select Research Branch

Speak to the human in Japanese; keep files in English.

1. Read context, goal, compact memory, idea bank, digest, and ledger. If the paper graph is non-empty, run one focused `pk.py brief` query for the current open question and include matched failures or gaps.
2. Each viable idea must have `id`, `status`, `hypothesis`, `rationale`, `novelty_axis`, `mechanism`, `why_now`, `expected_failure_mode`, `minimal_test`, `forbidden_by_policy`, `source_refs`, and `next_test`.
3. Exclude dead ends, forbidden ideas, simple replays, seed searches and exploratory micro-sweeps. Retain controls essential to the research claim, even before core evidence.
4. Work backward from GOAL's evidence strategy. Prefer a coherent method with high research decision impact and adequate comparisons, then minimize risk/cost. `minimal_test` means the next sufficient test for its stage, not the tiniest hypothesis; smoke only removes a readiness blocker. Identify necessary later evidence.
5. Present one primary branch and one fallback branch. Do not create an experiment unless the user asks for the next script step.
6. If no safe candidate exists, request `$scan-research-landscape` or human direction.

Boundaries: do not implement, train, evaluate, update baselines, or select exploratory ablations before core evidence. Route the primary branch to `$audit-novelty` then `$plan-experiment`.
