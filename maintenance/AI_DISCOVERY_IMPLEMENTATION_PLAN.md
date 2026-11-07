# Source-grounded scientific contribution: implementation plan

Date: 2026-10-22. Authorized maintenance: investigate research-agent papers,
synthesize their use, plan and implement improvements. The user's clarification
prioritizes new discoveries and substantive scientific progress over imitation.
No live experiment is active; this work does not authorize starting one.

## Evidence and observed gap

The review covers 19 distinct papers/work families: seven in
`AI_RESEARCH_LITERATURE_FOUNDATIONS.md`, eight in
`AI_RESEARCH_LITERATURE_RECENT.md`, and four in
`AI_RESEARCH_LITERATURE_BENCHMARKS.md`. Public primary abstracts, publication
metadata and official summaries were inspected. Versions are not independent
confirmations. Venue status is recorded; impact factors are not invented.

ResearchAgent/SciMON support source-grounded proposals; Virtual Lab,
Co-Scientist and Robin connect proposals to experimental observations. Their
reported cases do not establish general autonomous discovery reliability.
Si et al., DISCERN and Into the Unknown show why favorable novelty ratings,
task completion and fluent papers must remain distinct from supported advances.
These are design implications, not evidence that this patch improves discovery.

Existing `automation/RESEARCH_FOCUS.md` already rejects name-, dataset- and
score-only novelty. Existing plan fields cover alternatives, discriminating
evidence, falsifiers and matched controls. `research_memory.py` validates 2-3
closest-source comparisons and five novelty facets. `build_plan_review_bundle.py`
already hashes the full latest novelty record; `research_decision.py` snapshots
it. Reuse these mechanisms. The missing structured link is source observation
versus inference, substantive advance, and different observable predictions.

## Selected contract

New experiments created by `new_experiment.py` carry
`novelty_contract_version: "1.0"` in their script-owned manifest. Their usable
`proceed` novelty record must contain `contribution` with:

| Field | Requirement |
| --- | --- |
| `schema_version` | Exactly `"1.0"`; reject unsupported versions. |
| `kind` | `discovery`, `method_advance`, `boundary`, or `replication`. Classification is a claim, not proof. |
| `source_observations` | 1-3 distinct `{source, observation}` objects; sources must match existing `similar_items` source identifiers exactly. Statements must reflect the inspected source, including scoped absences. |
| `inference` | Unresolved question and proposed explanation/claim inferred from those observations. |
| `advance` | What becomes known or achievable and why it matters beyond a routine extension. For replication, explicitly limit the contribution to reproducibility/supporting evidence. |
| `alternative` | Strongest plausible explanation without the claimed new contribution. |
| `candidate_prediction` | Observable outcome predicted by the candidate under the proposed test. |
| `alternative_prediction` | Observable outcome under the strongest alternative; cannot be textually identical after whitespace/case normalization. Scientific distinctness still needs audit. |
| `discriminating_test` | Necessary contrast and matched controls linking the predictions to the existing plan. |
| `advance_criterion` | Preregistered condition for substantive progress, including a result that would defeat or narrow it; use existing primary decision rules, no extra promotion metric. |

All strings must be substantive, with existing placeholder conventions rejected.
No automatic language model judge or keyword-based truth detector is added.
Keep source and output budgets: 2-3 closest works, 700 plan words, existing
decision-response and audit-input limits. A compact realistic contribution must
fit an ordinary novelty response; do not expand budgets to accommodate verbosity.

## Integration and historical compatibility

1. Extend the existing novelty validator with an explicit `require_contribution`
   option and validate a supplied contribution even for legacy records. JSONL
   historical records without it remain readable and unchanged.
2. New experiment manifests opt into the contract. Unsupported manifest versions
   fail closed; absence means a legacy experiment. No bulk migration or rewriting
   accepted evidence. Document that legacy records are not retroactively upgraded.
3. For marked experiments, the ordinary novelty route, plan-bundle creation,
   accepted-plan-audit prerequisite and agent novelty acceptance require the
   contribution before any state/evidence mutation. Direct approval must encounter
   the same prerequisite through `require_accepted_plan_audit`.
4. Bind the marker in plan-audit input hashes and decision snapshots, conditionally
   for marked experiments to preserve old hash shapes. Full novelty contents are
   already bound; reuse that. A changed contribution invalidates a prior plan audit
   and pending decision. Do not add a second lock or new evidence store.
5. Map observations/inference into plan `Rationale`, contribution/advance into
   `Novelty check`, predictions/test into `Minimum discriminating evidence`, and
   the advance criterion into existing claim/decision/falsifier fields. Independent
   audit judges whether this mapping is scientifically faithful. The code only
   validates structure and provenance, not semantic equivalence or global novelty.
6. Update novelty, planning and hypothesis-generation guidance plus the delegated
   decision procedure. Preserve one hypothesis, essential controls, independent
   audit, no repeated reviewer votes and explicit-only agent-led execution.

## Ownership and bounded change list

One maintenance implementation worker owns runtime changes in
`scripts/research_memory.py`, `scripts/new_experiment.py`,
`scripts/next_autonomous_step.py`, `scripts/build_plan_review_bundle.py`, and
`scripts/research_decision.py`, with focused coverage in
`tests/unit/test_scientific_contribution.py` and only necessary existing fixtures.
The supervisor owns this plan, human synthesis, contribution guidance, skill
wiring, README/tree links and maintenance handoff. Preserve all pre-existing dirty
files; no Git reset, commit or external publication is part of this request.

Read budget for implementation: the five runtime files, the relevant existing
fixture/test modules (`test_research_memory`, `test_plan_audit`, `test_agent_led_loop`,
`test_autonomous_loop`) and directly required helper definitions; list paths first,
read bounded sections, at most 2,000 source lines initially. No recursive payload
or completed-experiment reads. Expand only for a concrete failing dependency.

## Acceptance checks

- New experiments opt in; existing legacy histories and accepted audits retain
  compatibility. Unknown versions and malformed contributions fail clearly.
- Accept valid discovery, method-advance, boundary and supporting-replication
  records without declaring any scientifically proven.
- Reject missing evidence, invented source identifiers, duplicate observations,
  empty/placeholder fields, unsupported kinds, and identical predictions.
- New-contract ordinary and agent-led pathways cannot bypass the requirement;
  rejection leaves state, novelty history and acceptance markers untouched.
- Changing contribution contents or the marker invalidates existing audit/decision
  provenance. Verify actual bundled contents and accepted-audit checks.
- A compact complete response fits the existing word budget and is accepted via
  the actual decision API; a fresh model run is not required for deterministic
  contract coverage and would not establish improved scientific quality.
- Run affected tests, then unit/smoke regression if integration changes warrant;
  run `scripts/validate.py`, focused lint, skill validation and whitespace checks.
  Confirm live research inputs remain byte-identical.

## Excluded scope and remaining evidence

No new model service, dependency, knowledge graph store, debate panel, tournament,
open-ended search, paper generator or automated training. Reproduction and smoke
remain valid supporting work but cannot establish discovery. Scientific progress
may include a boundary condition or negative finding; it need not be a higher score.
Actual effectiveness requires a separate matched-resource study on scientific
questions with preregistered contribution criteria and retained failures; a study
outline appears in `human/AI_DISCOVERY_REVIEW.ja.md`.

The supervisor integrated the concrete plan from the saved literature briefs and
bounded repository exploration. A separately assigned design worker failed with
model-capacity unavailability before returning a plan; it was not retried or
replaced. Its failure supplies no scientific evidence or approval.

## Implementation and verification record

Implemented the five runtime changes and focused tests described above; see
`AI_DISCOVERY_IMPLEMENTATION_RESULT.md` for the worker's evidence. No existing
test fixture or live research input required migration. The supervisor also
updated contribution guidance, the four phase skills, delegated decision
instructions, the experiment template and human/index documentation. The
closed plan-audit request now explicitly asks about source facts, substantive
advance and the mapping of rival predictions, test and criterion into the plan.

The worker reported 261 focused tests and 648 unit/smoke regression tests passing
(two pre-existing sandbox cases excluded; 13 subtests passed). A complete 181-word
synthetic novelty response passed the actual acceptance APIs under the existing
250-word budget. The supervisor's final integration checks are recorded in
`maintenance/HANDOFF.md`; the five live research input fingerprints matched.

An additional read-only reviewer returned BLOCKED because its governing role
permits only live experiment plan bundles. Its unchanged report is saved in
`AI_DISCOVERY_REVIEW_STATUS.md`. No source inspection occurred, no replacement
reviewer was launched and no independent implementation-audit success is claimed.
This optional review is not a mandatory maintenance completion gate. Scientific
discovery effectiveness remains unmeasured; tests verify structural/provenance
behavior only.
