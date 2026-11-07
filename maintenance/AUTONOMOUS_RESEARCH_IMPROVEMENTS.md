# Autonomous Research Agent Review and Implementation Plan

Reviewed 2026-10-22. Scope: public primary papers and official GitHub projects,
then improvements to this template. Repository pages are observations of the
linked branch on this date, not pinned upstream releases. No external project
was installed or executed. No live research experiment is authorized by this
maintenance task. Existing uncommitted changes remain in place.

## Sources and bounded findings

| Source | Observed design and limitation | Local implication |
| --- | --- | --- |
| [AI Scientist-v2 paper](https://arxiv.org/html/2504.08066v1), sections 3.2 and 5; [GitHub](https://github.com/SakanaAI/AI-Scientist-v2), [configuration](https://github.com/SakanaAI/AI-Scientist-v2/blob/main/bfts_config.yaml) | Stage manager, checkpoints, tree exploration and repeated seed evaluation; paper acceptance is a limited workshop result. Configuration bounds execution time and iterations. | Retain stage gates and fixed replications; do not import best-node selection or exploratory tuning into a locked comparison. |
| [Agent Laboratory paper](https://arxiv.org/html/2501.04227v2), sections 3.3.1 and 5; [GitHub](https://github.com/SamuelSchmidgall/AgentLaboratory), [workflow code](https://github.com/SamuelSchmidgall/AgentLaboratory/blob/main/ai_lab_repo.py) | Autonomous and human-feedback workflows; workflow code saves phase state and resets agent context. The paper describes unreliable self-evaluation and invented experimental details. | Preserve distinct human/agent authority, durable recovery and fresh contexts. A saved dispatch needs an actual worker identifier, not assumed liveness. |
| [AI-Researcher paper](https://arxiv.org/html/2505.18705v1), sections 3 and 6; [GitHub](https://github.com/HKUDS/AI-Researcher) | Separate resource, implementation and review stages; discussion identifies incomplete implementations and loss of detailed evidence in long-context summaries. | Use bounded source material and explicit evidence links instead of relying on prose assurances. Existing implementation audits already cover method fidelity. |
| [Kosmos paper](https://arxiv.org/html/2511.02824v1), sections 2.1 and 3 | Structured shared knowledge connects claims to analyses or publications. Evaluators found synthesis less reliable than direct observations; intermediate intervention was limited in this version. | Require traceable decision evidence and uncertainty. A citation does not prove entailment. This is a paper-only comparison; no official open orchestration implementation was verified. |
| [Hidden Pitfalls paper](https://arxiv.org/html/2509.08713v1), sections 3-7 | Controlled tests identify benchmark, leakage, metric and selection risks; workflow evidence improves inspection over final-paper review alone. Scope and test conditions limit generalization. | Preserve locked criteria, negative results and audit evidence. Retain compact decision artifacts, not raw traces prohibited by this repository. |

These implications are engineering judgments from the sources, not reproduced
performance claims. Source performance numbers do not predict this template's
research quality. No source claims that the following patch removes sycophancy.

## Current-state gaps

Inspection: `scripts/research_decision.py`, `scripts/next_agent_led_loop_step.py`,
`scripts/records.py`, `scripts/accept_human_interpretation.py`, and matching tests.
Live state is setup with no active experiment.

1. `_response` accepts a generic rationale citing only GOAL even for plan
   approval. It does not require discussing adverse evidence, uncertainty or
   the accepted audit. The existing independent-judgment instructions are not
   represented in the decision response contract.
2. `_snapshot` includes the entire experiment record, including draft conclusions,
   and planning guidance during result interpretation. This exposes a deciding
   worker to earlier agent conclusions beyond its necessary evidence.
3. Dispatch records contain only a request hash. The pending route cannot name
   the actual worker to inspect after interruption; it conflates pending and
   unavailable workers. Starting a substitute would violate existing rules.

## Selected changes and acceptance criteria

| ID | Implementation | Completion evidence |
| --- | --- | --- |
| D1 | New requests declare a bounded evidence assessment: cited observations, strongest counterargument, uncertainty and change condition. Plan approval must cite the plan and current audit and respond to its caveats; result interpretation must cite authoritative facts. Validate before state changes. | Valid approval/revision/inconclusive paths pass; missing or foreign evidence, missing uncertainty and audit omission fail with state unchanged. Existing source/word budgets and fail-audit blocks remain. |
| D2 | Reuse `plan_record_material` to include only hypothesis/method from the experiment record; omit planning guidance from result interpretation. Preserve required audits and facts. | Earlier conclusion text cannot appear in a request; modifying it does not create a new decision worker; scientific plan changes still invalidate a request. |
| D3 | Bind one returned worker ID to a dispatched request; repeated same-ID binding is idempotent, replacement is rejected. Return a check-worker action with the saved ID; the supervisor queries live tool status before waiting. | Test missing/stale dispatch, identity replacement, pending workers after input changes, saved response reuse and router integration; perform one gated fresh worker trial if available. |

Implement D1-D3 in the existing decision script, router procedure and focused
tests. Preserve one target, independent audits, no replacement workers/retries,
fixed compute and explicit invocation. Existing accepted evidence is untouched;
old unaccepted requests must not be silently upgraded or resubmitted.

## Alternatives considered

- Keep existing human checkpoints and implementation/provenance audits: already
  present; replacing them would duplicate mechanisms.
- Do not add tree search, reviewer voting or open-ended self-repair: these conflict
  with one coherent comparison, one auditor and no automatic retry constraints.
- Do not add a vector database or full world model: structured memory, hashes and
  decision facts already exist; the demonstrated gap is in decision handoffs.
- Do not implement paper generation or unattended full-compute approval: neither
  fixes these evidence/recovery gaps and both expand the authorized workflow.

## Verification record

Implemented D1-D3 in `scripts/research_decision.py`. The existing dedicated
router passes through the new check-worker action without changing other loop
policies. The decision procedure, entry skill and Japanese guide are updated.
New requests use schema 1.1. A bound worker ID is required before acceptance and
retained in ACCEPTED.json. No new dependency, research-state migration or model
configuration change was needed.

- Final unit/smoke regression: 475 passed, 2 unchanged SandboxTests deselected,
  13 subtests passed, using `<historical-test-environment>/bin/python -m pytest
  tests/unit tests/smoke -k 'not SandboxTests' -o addopts='' -q`.
- The final regression includes 41 decision-flow cases. A prior focused run
  passed 39 cases; the last two cover legacy requests before dispatch. The full
  suite was rerun after strengthening that guard, with no failures.
- `python3 scripts/validate.py`: zero warnings. Focused Ruff, skill frontmatter,
  and `git diff --check` passed. The entry skill is 2,157 characters, below 2,200.
- CLI checks confirmed explicit invocation is required, a missing worker ID
  produces one error line, and the live STATE.json remains byte-identical.
- One real, fresh, read-only frontier/high worker was launched only after a
  synthetic plan gate returned delegate. Its actual canonical handle was bound;
  the router returned check-worker; the live collaboration tool confirmed the
  worker; its unchanged 209-word response was accepted and returned the fixture
  to DRAFT. It requested revision despite an accepted warn audit, citing a
  missing matched baseline and inconsistent falsifier/promotion rules.

Trial directory: `<historical-trial-directory>`; experiment `EXP-AUDIT`;
worker `/root/decision_trial`; request digest
`ee9f1324894280a1d306cccf50b39af45938a37f8e99e8e145b956d1b7b57559`;
verbatim response SHA-256
`1c06df3f1cb34cdca0c63cf97b15261601d8b2411f60f62a415b61804e0dee46`.
Temporary trial artifacts are diagnostic evidence, not live research records.
The fixture comes from `_setup` in `tests/unit/test_agent_led_loop.py`; its
generated source observations are not real scientific results.

## Completion audit

| Requirement | Inspected evidence and result |
| --- | --- |
| Research GitHub and papers | Three official repositories, five primary papers and two bounded code/config files inspected; source table records URLs, sections, limitations and local implications. |
| Plan improvements from actual gaps | Current decision, routing and acceptance code inspected; D1-D3 each map an observed gap to a source-informed design and acceptance criteria. Alternatives are explicitly assessed above. |
| Implement every selected improvement | D1 evidence assessment and audit response checks, D2 plan-only source projection and guidance omission, D3 persistent handle binding and check-worker routing are active in the existing entry flow. |
| Reject invalid judgments without mutation | Parameterized tests reject missing assessments, uncertainty, audit responses, foreign/mismatched/repeated sources and malformed external URLs. Goal-only result interpretation and unbound-worker acceptance are rejected before state changes. |
| Preserve validity and recovery boundaries | Tests preserve fail-audit rejection, compute authorization, one target, worker/revision budgets, stale-input rejection, response reuse and negative/inconclusive finalization. Legacy unaccepted requests block instead of silently spawning replacements. |
| Verify actual integration | Fresh worker trial exercised gate, dispatch, binding, status inspection, original response storage, assessment validation and revision transition. Accepted metadata preserves worker identity. |
| Document and hand off | Japanese usage guide, README links, tree indexes and maintenance handoff updated. Live project remains setup with no active experiment. |

The code verifies evidence structure and provenance boundaries, not the truth of
observations or completeness of counterarguments. A single worker trial is not
a comparative sycophancy evaluation. No empirical claim about better scientific
discovery, external-system performance or statistical effectiveness is made.
