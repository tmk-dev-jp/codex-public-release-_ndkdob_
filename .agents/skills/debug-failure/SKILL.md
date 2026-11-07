---
name: debug-failure
description: Repair one failed experiment run or rejected audit through an isolated implementation worker.
---

# Debug Failure

The supervisor routes this phase and reads compact status only. Keep failure details, source and debugging history in a fresh worker context.

1. Run `python3 scripts/next_agent_action.py --task repair --id <ID>` before reading failure artifacts or source. On `build`, run `python3 scripts/repair_context.py prepare --id <ID>` and rerun the gate. Do not open REQUEST.json in the supervisor.
2. Only on `delegate`, start one fresh instance of the returned agent without inherited conversation. Give it only the request path and `automation/ISOLATED_REPAIR.md`. Do not resume the original implementer or forward earlier discussions, audit text, source, logs or test output.
3. The worker uses the locked profile/scope, repairs once, runs focused checks and `mark_implemented.py`, then returns only `repair_context.py status` output. A blocker report is at most 80 words without code or logs. No explorer, reviewer, fallback or replacement worker.
4. Independently run `python3 scripts/repair_context.py status --id <ID>`. On verified `status=implemented`, report only ID, changed-file count and next mode; stop. Do not ingest the delta, diff, failure or worker transcript. Pre-run audit and later execution remain separate.
5. On `blocked`, invalid status or unavailable worker, stop with the compact reason; do not debug in the supervisor or reuse stale context. Never change scientific criteria, retry training or erase comparison evidence.

Only an explicit human abort instruction authorizes `python3 scripts/abort_comparison.py --id <ID> --reason "<English reason>" --confirm-abort`. `Next` or unattended permission alone does not authorize aborting.
