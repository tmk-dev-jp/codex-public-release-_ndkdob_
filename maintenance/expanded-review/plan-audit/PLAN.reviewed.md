# Expanded anti-sycophancy maintenance plan

Date: 2026-10-22. Authorization: the user requests additional research, planning,
implementation, and subagent audits of both plan and implementation. This is
template maintenance, not authorization to execute a research experiment.

## Evidence and scope

The new read-only survey contains 11 distinct repositories and 15 distinct primary
papers, excluding the earlier 3 repositories and 5 papers. SURVEY.md and
SYCOPHANCY_SOURCES.md preserve the survey worker's returned text. Source coverage
includes research agents and explicitly labeled evaluation/recovery infrastructure;
these are not 11 demonstrated independent scientific discovery systems.

P12–P15 directly motivate user/peer preference reversals and evidence-change
controls. G05/P05 support artifact-bound attribution; G02/G11/P11 motivate durable
state identity. G09/P09 and P03 support retaining independent numerical and
integrity boundaries. These are design inferences, not proof that this template
reduces sycophancy. Upstream code was inspected, not executed or reproduced.

Local inspection found:

1. `accept_interpretation(..., source="agent_research_decision")` accepts the source
   label without the current dispatched-response proof required by `approve_plan`.
2. `accept_decision` writes several files and writes ACCEPTED.json last. A synthetic
   injected failure at that last write left no receipt while state already said
   `implement_experiment`. The fixture's unrelated scope preflight then blocked;
   this is evidence of partial acceptance, not evidence that compute was launched.
3. Independent-judgment prompts and structural tests exist, but no reusable local
   behavioral scoring fixture distinguishes resistance to social pressure from
   failure to update on actual evidence.

## Selected changes

### A. Bind interpretation authority to the saved decision

Require the agent interpretation pathway to prove the canonical current request,
dispatch hash, bound worker, valid response action, current facts/audits and exact
interpretation bytes. Reuse existing decision validation rather than a new identity
service. Validate before research-record mutation. Store response/request identity
and worker provenance with the accepted evaluation. Human interpretation retains
its existing pathway. Stored worker names are bookkeeping, not cryptographic host
authentication. Do not invent missing judgment or change an adverse verdict.

Acceptance: reject label-only calls, missing dispatch/worker, wrong action/path,
changed response text and stale facts before modifying state, manifest or records.
The ordinary accepted inconclusive result still finalizes with facts unchanged.

### B. Stop on interrupted acceptance

Use a small durable APPLYING.json intent immediately before the first research
mutation, after relevant validation, containing the same request/response hashes,
worker and action identity as the final receipt. A completed receipt must match
that identity. On an incomplete or mismatched intent, both decision entry points
and the agent-led router stop before another transition, worker or effect. Check
before routing code that may itself update state, including when state/manifest
phases differ after interruption. Completed historical decisions without the new
intent remain supported; unaccepted old decisions follow existing rules.

This is fail-closed detection, not transactional rollback, exactly-once execution,
or automatic recovery. Preserve the files and report the request path for scoped
maintenance inspection. Do not delete markers, replay acceptance automatically,
retry workers, or continue execution. Atomic individual file replacement remains
the persistence primitive. Power-loss durability and concurrent writers are outside
the existing single-supervisor contract; do not claim they are solved.

Acceptance: fault-inject before/after representative writes for approval, revision,
novelty and interpretation, and at the receipt. Verify blocking despite partial
phase change, no subsequent mutation or worker dispatch, immutable facts/audits,
and normal acceptance and routing when the receipt is complete. Rejected invalid
responses must not create intent before validation. Retain response limits and
worker/revision budgets. Prefer a narrowly scoped pre-write hook or extracted
validation over a generic transaction engine.

### C. Provide a diagnostic evaluation for user and peer pressure

Add a versioned offline fixture and a stdlib-only export/scoring CLI. Use at least
12 cases, six user-pressure and six peer-pressure, balanced across evidence-supported
support/reject/inconclusive outcomes. For each case supply two opposite-preference
variants with identical evidence and criteria, plus a changed-evidence control that
holds the preference fixed and requires a different outcome (at least 36 responses).
Peer claims are advisory; their cue never changes an accepted audit's actual status.
Each case has an explicit decision rule and source IDs; no LLM judge is required.

Export only prompts, IDs and response schema, never gold verdicts. Keep gold values
in the scorer fixture. Score separately: evidence-rule accuracy, unsupported verdict
changes within unchanged-evidence pairs, correct updates on decisive evidence, and
required source citation coverage. Report user and peer breakdowns. No single
aggregate success score: constant rejection/inconclusive or indiscriminate agreement
must fail accuracy and/or update controls. Reject incomplete, duplicate, unknown or
malformed response batches rather than silently scoring a favorable subset. Preserve
input response files. Prevent output from overwriting fixtures or response inputs.

Document a fixed-order, fresh-context protocol recording model, settings, policy,
sample count and all raw responses. No API integration, model spending, automatic
repeated runs or model-judged scientific truth. This task verifies fixture/scorer
behavior with synthetic responses; actual comparative model efficacy remains
unmeasured. Identity swaps, neutral baselines and non-decisive-evidence variants
are future coverage, explicitly excluded from current efficacy claims.

## Alternatives and exclusions

A generic workflow framework, SQLite migration, reviewer voting, automatic repair
or transaction replay are disproportionate. Full recovery needs separate design;
preserving and blocking partial writes is the selected bounded safeguard. Do not
import upstream tree searches, tournaments, best-seed selection or changing success
criteria. An always-dissenting agent is not the target. Preserve justified agreement,
negative results, independent audits, locked controls and script-owned facts.

## Implementation contract

One fresh implementation worker, model `gpt-6-astra`, reasoning `high`, no inherited
history: this locked profile is justified by evidence provenance and transition
changes. The worker is not alone; preserve all other edits. Own only:

- scripts/research_decision.py
- scripts/accept_human_interpretation.py
- scripts/approve_plan.py (only if a narrow validated pre-write hook is needed)
- scripts/next_agent_led_loop_step.py
- scripts/evaluate_sycophancy.py (new)
- tests/unit/test_agent_led_loop.py
- tests/unit/test_sycophancy_evaluation.py (new)
- tests/fixtures/sycophancy/cases.json (new)
- .agents/skills/run-one-agent-led-loop/references/DECISIONS.md

Read budget: list paths first; read these existing files plus scripts/common.py,
scripts/return_plan_to_draft.py, scripts/workflow.py, scripts/AGENTS.md, the plan and
audit records. Additional named fixture helpers only when required, at most 3,000
code lines initially. No payload directories, completed experiments, unrestricted
repository exploration or live research-state writes. Parent owns docs, evidence
records, handoff and integration. No unrelated refactors or dependencies.

## Independent audits and validation

Before implementation, one fresh read-only frontier/high subagent audits this plan,
survey, policy and named transition sources. Preserve its exact verdict and
findings; record concrete dispositions separately. Do not replace a disagreeing
reviewer. After implementation and checks, a different fresh read-only frontier/high
subagent audits the implemented contract and tests, including how the evaluation
could be gamed. Preserve its exact report and resolve findings with scoped fixes
and verification. No reviewer panel or automatic re-audit.

Run focused transition/evaluation tests, then the established unit/smoke suite
excluding the two unchanged sandbox integration cases. Run scripts/validate.py,
focused Ruff and git diff --check. Verify all source counts, raw audit reports,
dispositions and human-facing documentation. Record the exact tests and limitations
in the maintenance handoff. Never report synthetic scores as model performance or
static invariants as measured sycophancy reduction.
