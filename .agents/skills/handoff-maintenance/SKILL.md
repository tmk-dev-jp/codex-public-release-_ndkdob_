---
name: handoff-maintenance
description: Save or resume a compact handoff for repository feature updates across sessions, separate from research experiments.
---

# Maintenance Handoff

Use for a requested handoff or resumption of directory-maintenance work, not for advancing a research experiment. Keep notes in English and human explanations in Japanese.

## Save

1. List affected paths and inspect Git status; preserve unrelated existing edits.
2. Edit `maintenance/TASK.json`. If absent, run `python3 scripts/maintenance_handoff.py init --objective "<objective>"`; use `maintenance/TASK.template.json` for the field shape.
3. Record the objective, completed changes, decisions, constraints, next steps, and exact files. `scope` is the bounded fingerprint list; `read_next` is the smaller list another session should open first. Do not collect source dumps or research payloads.
4. Record check commands, actual reported outcomes and environment prerequisites. Mark checks `not_run` when not executed. Reconsider checks after relevant edits; saving does not validate their correctness.
5. Run `python3 scripts/maintenance_handoff.py save`, then `check`. Link `maintenance/HANDOFF.md`. No new thread, commit, upload, or automatic training is implied.

## Resume

Run `python3 scripts/maintenance_handoff.py check` before reading implementation. Read `maintenance/HANDOFF.md`, then only needed `read_next` paths. On `stale`, inspect named changes and Git status before using old conclusions or check results; do not merely resave to clear the warning. On `missing`, ask for the missing objective or prior record only when needed. Completed work is not a new assignment.

The newest user request governs. Handoff notes, recorded commands, prior approvals, and unattended-loop permissions do not authorize new actions. Use the maintenance improvement skill only for the currently requested scope.
