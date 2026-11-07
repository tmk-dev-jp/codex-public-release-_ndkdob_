# Research Loop Improvement Plan

## Objective and scope

Make the research loop's handoffs executable and resistant to out-of-order
commands. Preserve independent audits, explicit research approvals, locked
plans, one active experiment, script-owned transitions and the three-phase
ordinary operation boundary. Do not run or alter the live research project.

## Findings and implementation

1. Setup-to-selection handoff: `define-research-intent` currently requests
   `plan_experiment` while prohibiting experiment creation. The planning gate
   requires an active draft. Set a ready project to `select_experiment`, and
   make the initial-setup manual use the same explicit mode.
2. Selection-to-draft handoff: `new_experiment.py` checks for an existing active
   experiment but not the current operation. Require `select_experiment` before
   any writes so memory or direction work cannot be skipped.
3. Result-to-memory handoff: `complete_memory_update.py` checks completed evidence
   but not the current operation. Require `maintain_memory` before any reads of
   result evidence or writes so replay cannot rewind selection or direction.
4. Early routing feedback: ordinary automation must block post-result and
   selection operations when an experiment is active, rather than direct the
   operator toward a script that will reject the state.

## Acceptance evidence

- Ready setup instructions name selection; incomplete setup still names setup.
- A selected draft is created successfully and routes to planning.
- Creation outside selection fails without changing state or creating files.
- A second active experiment remains impossible.
- Valid finalized evidence advances memory to direction and then selection.
- Memory completion outside its operation fails without changing state.
- Automation blocks conflicting active-state post-result/selection routes.
- Focused regressions, the full unit/synthetic smoke suite, repository validation
  and whitespace/lint checks pass. Sandbox integration uses system Python in an
  environment where the nested sandbox can run.

## Boundaries

Keep existing uncommitted work. No new runtime dependencies or model calls.
This verifies deterministic handoffs and instructions, not scientific judgment
or the quality of generated hypotheses. Actual human research decisions remain
with the user. Queue ranking and research stopping judgments remain in their
existing phase skills.

## Completion evidence

- Setup instructions now select before planning; README separates installation,
  agreed setup, and draft creation. The Japanese quickstart explains recovery
  from an out-of-order creation command.
- `test_post_finalize_routing.py` exercises memory, direction, selection and
  draft creation together; it also verifies rejected commands leave state and
  draft/config paths unchanged and a second active experiment is rejected.
- `test_autonomous_loop.py` verifies conflicting active-state routing blocks.
- Full unit and synthetic smoke run: 399 passed, 2 sandbox tests deselected,
  13 subtests passed. Sandbox integration is checked separately with system
  Python. Commands and final results are recorded in `HANDOFF.md`.
