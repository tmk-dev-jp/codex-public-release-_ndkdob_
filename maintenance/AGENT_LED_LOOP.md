# Separate Agent-Led Research Loop

## Scope

The requested new route delegates scientific decisions that ordinarily require
a human. It does not change the ordinary or unattended loop's approval rules.
The entry skill is `run-one-agent-led-loop`; its dedicated router uses the
existing lifecycle with separate `STATE.agent_led_loop` recovery state.

## Decisions and provenance

- Novelty questions use bounded source comparisons. High-risk or rejected work
  requires a substantive revision before clearance; sources and the resolved
  objection remain recorded.
- A fresh frontier/high decision worker may approve a current independent pass,
  accept nonblocking warn limitations with reasons, or request revision. Fail
  cannot be approved. Revision returns the same target to DRAFT, supplies scoped
  guidance, and requires a new lock and independent audit.
- Result interpretation reuses authoritative decision facts and required
  integrity audits. Support, rejection and inconclusive results can finalize.
  The manifest explicitly identifies agent judgment; no human file is fabricated.
- Requests, dispatch markers, responses and accepted metadata remain under
  `review/decisions/<ID>/`. Input fingerprints reject stale decisions. A dispatch
  marker prevents replacement workers; another pending worker blocks parallel
  decision-making. Six workers and two plan revisions bound each target.
- The target remains fixed through finalization, memory and direction update.
  Existing full-compute approval, external access, missing setup/data, execution
  failure and failed integrity gates remain enforced. No live research is started
  by creating this feature.

The decision worker receives only its request and procedure with no inherited
conversation. Its model is `gpt-6-astra`, high reasoning. This is a decision
author, separate from the independent audit role. Existing implementation model
profiles are unchanged.

## Verification

- Unit/smoke suite: 451 passed, 2 sandbox integration cases deselected, 13 subtests
  passed. Sandbox code was not changed.
- Nineteen new tests cover authorization, separate loop state, pass/warn approval,
  fail-to-revision, stale inputs, false source labels, source-backed novelty,
  high-risk/incomplete novelty rejection, dispatch reuse, target identity, worker
  and revision budgets, explicit stops, and result-to-finalization behavior.
- Local and independently audited synthetic comparison runs both accept an
  inconclusive agent interpretation, preserve decision facts byte-for-byte,
  finalize with source attribution, and route to memory update.
- One fresh frontier/high worker exercised the real gate in an isolated temporary
  fixture. It chose revision, citing a missing matched baseline and conflicting
  falsifier/promotion criteria. Its unchanged response was saved and accepted,
  returning the fixture to DRAFT. This revealed that revision instructions can be
  a list; the acceptor now joins list items without changing their meaning.
- Skill validation, repository validation, focused Ruff checks and diff whitespace
  checks pass. The test environment uses `<historical-test-environment>`; skill
  validation uses system Python with PyYAML.

The live project remains at initial setup. Synthetic tests and one decision-agent
trial establish routing and acceptance behavior, not scientific success or an
end-to-end live autonomous research experiment.
