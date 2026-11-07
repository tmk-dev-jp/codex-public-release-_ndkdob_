---
name: run-one-agent-led-loop
description: Complete one research experiment with delegated scientific judgment when the user requests an agent-led loop, including novelty, plan decisions and result interpretation.
---

# Run One Agent-Led Loop

Use only for a current request delegating research decisions for one loop. Keep files in English; report in Japanese.

1. Read context and state. Run `python3 scripts/next_agent_led_loop_step.py --explicit-user-request`. Retain the target ID; pass `--target <ID>` thereafter, after finalization.
2. Follow its subordinate phase skill. This invocation authorizes one target, bounded scientific decisions, pre-execution revisions and ordinary plan approval. Override human-decision/operation stops only through this route. Keep independent audits and locked execution controls.
3. For `issue=...`, read [decision procedure](references/DECISIONS.md). Follow its prepare/gate/dispatch/bind-worker/accept steps. Spawn only on `action=delegate`: one fresh default agent, model `gpt-6-astra`, reasoning `high`, no history; pass the request path and procedure. Require read-only work and save its response verbatim. Reuse saved output; never replace a worker.
4. If a phase needs scientific design consultation, use the same procedure with `--issue design --question "<specific unresolved choice>"`. For result interpretation use `--issue interpretation`; do not fill a human-authored file. Missing evidence can justify inconclusive, never invented facts.
5. After accepted revision, use the planning gate and `$plan-experiment` with active `RESEARCH_GUIDANCE.md`. Relock and obtain a fresh independent audit. Reroute after each action; evidence/gate changes count as progress.
6. Continue through finalization, memory and direction update. Finish only on `complete`; do not create another target.

At most six decision workers and two plan revisions per target. No execution retries. Missing goal/data/access, unapproved full compute or broader sources, failed provenance/integrity, exhausted limits or unavailable workers remain stops. Recover formatting within the phase using `automation/PRESENTATION_REPAIR.md`.
