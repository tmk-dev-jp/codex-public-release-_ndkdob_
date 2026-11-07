# Delegated Research Decisions

This is the scientific decision procedure for `$run-one-agent-led-loop`. It is
not an alternative auditor. The existing plan, implementation and integrity
auditors remain independent and retain their verdicts.

## Supervisor

The dedicated router binds `STATE.agent_led_loop` separately from the old loop.
Its saved target is recovery state, not fresh authorization. Invoke this route
only when the user delegates research decisions for one experiment.

For the routed issue, run these commands with the same ID, issue and optional
`--question` throughout:

```text
python3 scripts/research_decision.py prepare --id <ID> --issue <ISSUE> --explicit-user-request
python3 scripts/research_decision.py gate --id <ID> --issue <ISSUE> --explicit-user-request
```

On `action=delegate`, run `dispatch` with those arguments immediately before
starting one fresh default subagent with model `gpt-6-astra`, reasoning `high`,
and no inherited history. Give it only this procedure and the returned request
path. Require read-only work. It must return its JSON response, not edit files.
Immediately bind the returned worker ID with `research_decision.py bind-worker`
using the same arguments plus `--worker-id <ID>`. This is an identity record,
not evidence that the worker is running. Canonical task names are also accepted.
After a session change, verify from tool history that the handle still belongs
to this dispatch; a reused name alone is insufficient. Acceptance requires a
bound handle. The same ID can be bound again; a
different ID is rejected. On `action=check-worker`, inspect that exact worker
through the available collaboration tool. Wait only after confirming it is
live; use its saved output if completed. A timeout alone is not failure. If the
handle is missing or terminal without output, report that condition and stop;
never launch a replacement or clear the dispatch marker. If another request's
worker is returned, inspect it but do not apply its response to the current
request. Stale responses still fail acceptance.
Save the returned JSON verbatim as `RESPONSE.json` beside `REQUEST.json`; then
run `accept` with the same arguments and reroute. A malformed response may be
corrected only under the presentation-repair policy, preserving the original.
Do not invent missing judgment. A dispatched request without a response means
wait for that known worker, or report its unavailability; never launch another.

Before `prepare`, obey the gate: an existing response goes to `accept`, and an
existing request goes directly to its gate. Request hashes bind the goal, plan,
config, scope, novelty, audits and authoritative result facts. Changed inputs
invalidate a response. Preserve all decision folders as evidence.
Requests use schema 1.1. Existing unaccepted legacy requests require explicit
review, not automatic conversion or another worker. Accepted historical records
remain unchanged. Experiment sources contain only the locked hypothesis and
method; result requests omit planning guidance and previous conclusions. This
projection preserves required audits, controls and authoritative facts.

New acceptances write `APPLYING.json` after validation and before the first
research mutation. `ACCEPTED.json` must match that intent and the saved request,
response, dispatch and bound worker. Ordinary mutation gates and routers check
these records even after the original decision snapshot changes. If acceptance
is interrupted or its evidence changes, stop and preserve every file; report
the request path for scoped maintenance inspection. Do not delete markers,
replay acceptance, continue a human pathway, or replace the worker. This detects
partial acceptance; it does not roll back writes, authenticate workers, guarantee
power-loss durability or support concurrent writers. Historical receipts without
the new intent retain compatibility. Agent interpretations require the current
dispatched response and its exact interpretation bytes; a source label is not
authority. Duplicate direct agent acceptance is rejected, including after the
experiment reaches READY_TO_FINALIZE.

A phase asking for a human scientific choice uses issue `design` while DRAFT or
PLANNED, or `interpretation` after required result audits. Describe the actual
choice using `--question`; do not convert missing access or budget into a
scientific preference. Phrase the question neutrally: omit preferred verdicts,
peer consensus and supervisor confidence, while preserving material objections
and required audits. Revised plans use the ordinary planning gate with
`RESEARCH_GUIDANCE.md`, relock, and receive a fresh independent audit. This is a
new plan revision, not a second vote on an unchanged audit.

## Decision agent

Read only REQUEST.json. For novelty, the invocation also permits at most 2-3
highly similar titles/abstracts/snippets using obvious goal-scoped queries.
Existing source IDs may be used as evidence supplied in the request. No full
papers, downloads, broad repositories, raw data, checkpoints or code exploration.
Do not write, delegate further, call mutation scripts or infer external approval.

Return one JSON object with `action`, a substantive `rationale`, and nonempty
`evidence_refs` containing exact supplied source paths (or HTTPS URLs for scoped
novelty search). Each distinct source appears once in `evidence_refs`. Include
`assessment` with these fields within the existing total response word budget:

- `observations`: one to six objects with `source` and `observation`. Link a
  specific observed fact or documented absence to its source. The distinct
  source set must equal `evidence_refs`; repeated agents citing a source do not
  add independent observations. Do not treat a goal as an experimental result.
- `counterargument`: strongest plausible competing explanation or objection;
  if none is supported, explain that without inventing disagreement.
- `uncertainty`: the actual limitation or missing evidence.
- `change_condition`: evidence or an identified error that would change judgment.
- `audit_response`: required for plan approval. Explain how the current audit's
  caveats and required action are satisfied or bounded. Cite both EXPERIMENT.md
  and PLAN_AUDIT.md in observations. A fail still cannot be approved.

Interpretation observations must cite DECISION_FACTS.json. URL validation checks
format, not retrieval or scientific entailment; verify sources within the
authorized search scope. A supervisor must not fill missing assessment content
on behalf of the worker. Address the research question, proposed novel contribution,
strongest alternative explanation, discriminating evidence and remaining
uncertainty. Never optimize for completing the loop or obtaining a favorable
verdict. Negative and inconclusive outcomes are valid.

User preference, supervisor confidence and peer agreement are not evidence.
Form an assessment from supplied evidence and criteria before weighing prior
interpretations. Trace repeated claims to their original source; repetition is
not independent corroboration. Do not manufacture disagreement. In existing
rationale fields, name decisive evidence, uncertainty and what would change the
assessment. Change conclusions only for new evidence or an identified reasoning
error. Preserve unresolved objections and required audit gates; never override
machine facts. Reversing only a user's or peer's preference must not reverse the
verdict. Stay within the existing source and output budgets.

Allowed actions:

- `record_novelty` for issue `novelty`: include a complete `novelty` object with
  experiment_id, idea_id, query_terms, 2-3 distinct similar_items objects
  (source/shared/difference), facet_comparison (mechanism/condition/data_regime/
  objective/implementation_change), novelty_claim, risk, decision and
  human_review_needed. Proceed only with adequate evidence, low/medium risk,
  decision=proceed and human_review_needed=false. A prior high-risk/rejected claim
  requires substantive plan revision before clearance. After revision, also
  explain `resolved_objection`; a renamed method is insufficient.
  Include `contribution` for contract version 1.0: `schema_version="1.0"`, `kind`
  (`discovery`, `method_advance`, `boundary`, `replication`), 1-3 distinct
  `source_observations` (`source`, `observation`, matching `similar_items`),
  `inference`, `advance`, `alternative`, `candidate_prediction`,
  `alternative_prediction`, `discriminating_test`, and `advance_criterion`.
  State source facts separately from inference, meaningful progress, different
  observable rival predictions, matched controls and a defeating outcome. Keep
  the existing response budget; replication and feasibility do not prove discovery.
- `approve` for issue `plan`: accept a current independent pass or acknowledge
  each nonblocking warn limitation with evidence. Fail cannot be approved.
- `revise` for issues `novelty`, `plan` or `design`: include concrete
  `instructions` (a string or list of strings) that resolve the named objection while preserving GOAL,
  available data, resource limits, essential controls and one coherent comparison.
  Do not weaken the claim merely to fit a cheap test. Revise before execution;
  subsequent experiments and result-dependent rule changes are excluded.
- `interpret` for issue `interpretation`: include an English `interpretation`
  Markdown string with `## Conclusion` and `## Issues and Next Direction`.
  Fill Decision (support/reject/inconclusive), Mechanical rule status,
  Decision-rule assessment, Primary result, Baseline comparison, Supported scope,
  Unsupported or missing evidence, Confidence and caveats, Main issue,
  Next action and Stop condition. Copy the exact machine rule status. Use all
  required comparisons and only the preregistered rule. Missing observations or
  unresolved ambiguity justify inconclusive with a concrete next step, never
  an invented trend or human opinion. The result is recorded as agent judgment.
- `stop`: name the actual missing external prerequisite or why no adequate
  within-scope revision remains. Do not use this for an ordinary decision you
  can resolve from the evidence.

The response budget is 250 words, or 400 for interpretation, including JSON
fields. Requests retain the configured 9,000-character audit-input budget.
There are at most six decision workers and two plan revisions per target;
unchanged unresolved decisions do not get repeated votes. These bounds prevent
indefinite revision. Unapproved full compute, unavailable data/access, broader
sources, execution failure and failed integrity remain external or validity
stops. Scientific uncertainty alone can be recorded as inconclusive at the
result stage and finalized through the ordinary checks.
