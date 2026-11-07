---
name: implement-experiment
description: Implement an approved locked experiment within its declared scope before execution.
---

1. Run `python3 scripts/next_agent_action.py --task implementation --id <ID>`. It checks approval, hashes, read budgets, profile, and the locked delta. Stop unless it returns `delegate`.
2. Delegate once to the returned agent in a fresh context with locked-record paths, not the supervisor transcript. Keep the locked profile; no explorer or reviewer.
3. Worker only: start with budgeted `implementation_entry_reads` at the smallest relevant symbol/range. Expand scoped reads one file at a time only when current code or a focused test names a concrete reason. Never preload source.
4. Edit only each `change_targets` path and symbol. Implement the locked novelty test and comparison arms; preserve all locked scientific controls, invariants and baseline behavior. If the change no longer answers the research question, request plan revision.
5. After tracing the scoped flow, apply the minimality ladder: skip, reuse, stdlib/platform or installed dependencies, then minimum code. Add no speculative abstraction or dependency. For a behavior-preserving repair, fix the shared root cause; scientific expansion requires plan revision.
6. Add checks only for scientific validity or stable contracts, with focused tests for shapes, splits, determinism, finite values, metric behavior, and checkpoint behavior when relevant. Keep validation-loss checkpointing and early stopping.
7. Do not hand-tune learning rate or batch size. `mark_implemented.py` applies the deterministic stage policy and permits only those two managed config changes.
8. If the locked profile is too weak, scope is insufficient, or ambiguity remains, stop and request plan revision. Do not retry or switch agents. A later explicitly revised operation may escalate at most once.
9. Worker runs targeted checks and `python3 scripts/mark_implemented.py --id <ID>`; return only its OK line, or a blocker within 80 words. Keep source, diffs, test output and investigation in the worker. Supervisor checks the next router state without reading those details. Stop before training.
