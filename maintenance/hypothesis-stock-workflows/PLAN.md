# Proposal: evidence-bearing hypothesis stock and controlled promotion

Status: proposal only. Prepared 2026-10-24 (Asia/Tokyo). Source comparison:
[SURVEY.md](SURVEY.md). Current behavior: [REPOSITORY_REVIEW.md](REPOSITORY_REVIEW.md).
No production code, model trial, live idea or research queue change is part of
this request. The expected benefits below are hypotheses to test.

One independent audit returned REVISE on the frozen `PLAN.reviewed.md`. Both
findings are addressed in this revised specification; see
[AUDIT_DISPOSITIONS.md](AUDIT_DISPOSITIONS.md). The audit is not relabeled PASS,
and the revision has not received a second independent audit.

## Objective and explicit limits

Maintain a reusable stock of distinct, falsifiable hypotheses that appear to add
something to the closest inspected work, and promote only a reviewed revision
when an experiment is needed. “Eligible” means test-worthy within the recorded
scope. It never means undiscovered worldwide, true, or approved for execution.

Reuse `research/ideas/IDEA_BANK.jsonl` and the existing experiment novelty,
plan-review, policy and one-active-experiment gates. Do not create a parallel idea
database, graph service, tournament, continuous background agent or new model
dependency. Qwen3.8 remains offline. Any later model trial must preserve the user's
runtime choice; provider failure is recorded, not silently substituted.

## Workflow and agent responsibilities

1. **Scope and retrieve.** The supervisor checks direct user authorization or the
   existing unattended replenishment boundary, the goal, exclusions, source scope
   and resource cap. A scout retrieves two or three closest canonical works per
   candidate, recording queries, sources, dates, routes and access gaps. A graph
   brief is a lead until checked against its underlying source.
2. **Generate a bounded batch.** One generator produces up to three candidates
   per invocation, including zero if evidence is inadequate. This cap is a
   proposed operating default, not a scientifically optimized parameter. Useful
   routes include contradictory findings, boundary conditions, unexplained
   failures and a justified cross-domain mechanism. No quota per route is imposed.
3. **Store and compare.** A script validates identity/provenance and appends a
   revision to the existing bank. Compare its mechanism, conditions, competing
   explanation and test with prior candidates. Exact identity collisions fail;
   semantic similarity only nominates a pair for review. Retain rejected and
   duplicate records with a reason and a target, rather than delete history.
4. **Independently screen.** One read-only reviewer per candidate revision receives
   the claim, source evidence, closest-work comparison, alternatives and proposed
   test. Hide generator confidence, prior votes, names/prestige and desired
   outcomes; retain scientifically relevant evidence and source identities.
   The reviewer commits an initial evidence-based assessment before seeing prior
   evaluative feedback. A final reconciliation records any changed conclusion and
   its evidentiary reason. No majority vote or replacement reviewer is permitted.
5. **Retain or defer.** Store the decision and unresolved objections against that
   exact revision. Revisiting a failed candidate requires new evidence or a
   specific identified reasoning error, not a new wording or repeated votes.
   Preserve both predictions and the observation that would defeat the claim.
6. **Promote explicitly.** When no experiment is active and the existing router
   requests selection, one script promotes at most one eligible revision into
   `research/QUEUE.json`. Rank eligible candidates by decision value, feasibility
   and portfolio coverage using written reasons; no scalar novelty threshold.
   The selected experiment still passes the existing novelty and plan gates.
7. **Feed back accepted outcomes.** After normal experiment evaluation, link
   accepted evidence, negative results and inconclusive results to the original
   revision. Distinguish an agent's report from independently accepted evidence.
   Refill only at an authorized boundary, not automatically after every message.

Each delegated phase still needs a script gate and an allowed profile. These
roles are responsibilities, not a requirement for seven processes or concurrent
panels. Reuse existing scout/planner/reviewer capabilities. Minimal rollout keeps
stock generation at the current no-active-experiment selection boundary.

## Versioned record contract

Extend the current idea record with `stock_contract_version: 1`. Retain all
existing required fields. The record's `id` becomes a unique immutable revision
ID for this version; `candidate_id` groups revisions and `parent_revision_id`
points to an existing revision of that candidate. Legacy records remain readable
under their existing contract. New stock operations cannot write legacy records.

| Field group | Required meaning for new records |
| --- | --- |
| Identity | Unique `id`, stable `candidate_id`, nullable parent, creation time, and a script-computed canonical content hash. No edits to prior revisions. |
| Scientific claim | Mechanism, conditions/data regime, predicted observation, strongest alternative with its different prediction, discriminating test, failure criterion and expected decision impact. A changed claim/test creates a new revision. |
| Provenance | Source observations with resolvable source IDs and precise locators; generated inference separately tagged; source type distinguishes publication, dataset, accepted experiment and unverified agent report. |
| Search record | Query, provider/index, access time, searched scope/date filters, retrieved canonical work IDs, source version, limitations and `complete_within_scope`, `incomplete` or `failed`. Completeness is a report about the declared search, not the literature. |
| Prior-work comparison | Two or three closest canonical works, shared features, concrete differences, five existing novelty facets and unresolved overlap. arXiv versions and paper/code/project pages for one work are not independent supporting works. |
| Lineage/duplication | Parent revision; explicit `duplicate_of`, `supersedes` or `related_to` links where applicable; review rationale. No self-links, dangling links or cycles in parent/supersedes chains. |
| Review and applicability | Immutable review reference/hash and reviewed content hash, independent verdict and objections, goal/policy snapshot hashes, search recheck condition or declared expiry, and current state. |

The content hash excludes the review attachment and script-generated hash itself,
avoiding a circular hash. It covers scientific content, source/search evidence,
comparisons and goal/policy snapshots. A review binds to that content hash. Adding
the review and state appends a new record revision with the same scientific
content hash, never overwrites the reviewed record. Promotion binds to the final
revision ID plus its full serialized-record hash and review hash. Canonical JSON
uses stable key order and UTF-8; document the exact serialization in one helper.

Use five states: `candidate`, `eligible`, `deferred`, `rejected`, `superseded`.
Screening appends one decision revision. `candidate -> eligible` requires a
complete scoped search, sufficient canonical comparisons, resolved material
objections, a discriminating test, source access adequate for the claim, current
policy compliance and a bound independent review. Unresolved novelty, unavailable
sources, missing comparisons or expired evidence produce `deferred`; a known
duplicate or refuted premise produces `rejected`. The explanation is mandatory.
Revising any decision begins a new `candidate` revision with an evidence/error
reason. Superseding a record preserves it and its outgoing provenance.

An eligible record is usable only if it is the candidate's current revision and
its review/goal/policy/freshness bindings remain valid. Newly discovered closest
work, a material contradiction or changed goal/policy invalidates eligibility
before selection. A configured expiry may trigger recheck; no universal number
of days is asserted here. Store the actual expiry/recheck policy with the review.
Invalidation is checked before use and does not require an autonomous scheduler.

## Script-owned operations and compatibility

Proposed `scripts/hypothesis_stock.py` exposes small operations to validate/append
a candidate, attach a review decision and promote one revision. Reuse validation
helpers in `scripts/research_memory.py`; do not duplicate eligibility rules in
the CLI, router and experiment creation. Each CLI invocation emits one `OK ...`
or `ERROR ...` line. Source/provider failures are explicit and have no hidden
retry or automatic model fallback.

**Stock-only writes:** candidate/review operations touch the bank and their
scoped evidence files only. `QUEUE.json` and `STATE.json` remain byte-identical.
The supervisor and reviewer do not directly edit lifecycle records.

**Promotion:** under one repository writer lock, re-read the current bank, queue,
goal/policy and research state; enforce no active experiment and selection mode;
validate exact revision, review, sources and applicability; reject a different
live queue entry for the same candidate; append one queue entry by atomic replace.
Record candidate/revision IDs, full revision hash, review hash, contract version
and a deterministic promotion key. Promotion writes only the queue, avoiding a
cross-file transaction. Retrying the same valid request returns the existing ID;
changed/invalid bindings fail. No promotion status mutation of the bank is needed.

Define one deterministic `queue_payload(revision)` projection for all scientific
queue fields: the hypothesis, rationale/decision impact, mechanism, conditions,
predictions/alternative, minimal test, novelty comparison and evidence references.
Store its canonical hash in the immutable admission envelope together with the
revision/review bindings. Routing and creation recompute the projection from the
reviewed revision and compare both the envelope and the actual queue content.
The field mapping is shared with the writer. Any additional claim-bearing field
must be included; unknown non-operational fields fail. Operational changes are
limited to `status`, an assigned experiment ID, and result-reference metadata,
through existing lifecycle helpers. They cannot change the scientific payload.

Candidate/review writers must use the same lock. Router selection and
`new_experiment.py` recheck the shared predicate; creation checks and consumes the
entry under the same lock to avoid a validation-to-use race. Existing record/state
helpers remain responsible for their transitions and experiment artifacts.

**Legacy migration:** introduce one small script-owned admission manifest listing
pre-existing queue IDs, canonical hashes of their scientific admission contents,
initial lifecycle status and irreversible retirement state. It is an admission
ledger, not a second hypothesis store. Generate a dry-run report first; the actual
one-time migration records the current baseline before enabling the new contract.
Do not auto-extend it during validation. Keep legacy entries permanently: no
supported operation may remove, replace or reinsert a legacy ID. An append checks
all IDs in the ledger, not just those currently visible in the queue.

Existing entries with unchanged content keep their current selection rules and
policy checks until consumed or retired. Existing lifecycle helpers must enforce
an explicit transition table: selectable states can remain selectable or advance
to consumed/retired; consumed/retired is irreversible and cannot become selectable.
Map the repository's actual status vocabulary to these classes during the bounded
writer inventory. Ambiguous/unknown statuses fail migration readiness instead of
being guessed. Terminal entries are retired at migration.

Record consumption/retirement in the ledger under the same writer lock **before**
updating the queue or creating the experiment; selection always consults it.
On an interrupted multi-file transition, fail closed and use an explicit recovery
operation that completes the recorded transition without restoring eligibility.
No automatic retry/re-admission is allowed. This small write-ahead retirement
record is needed for the legacy path; ordinary new promotion still writes only
the queue. Detect missing legacy entries at validation and require explicit
recovery; a same-ID append is never the recovery mechanism. Direct filesystem
rewrites outside the script contract are not a supported lifecycle operation;
this design does not promise to detect an unobserved removal and exact restoration
of every persisted file.

All post-migration queue admissions require the new contract. Deleting the origin
field or claiming a legacy version cannot create a grandfathered entry. A changed
legacy claim must enter the new path with a new ID; its old ID remains retired.
Legacy ideas stay readable but require a new reviewed revision before admission.

Adapt all authorized queue-writing paths in the bounded implementation inventory
to the promotion helper, including replenishment and result-derived direction
updates. If a writer cannot yet satisfy the new contract, fail explicitly rather
than produce an apparently ready item. Preserve current accepted experiments and
their evidence; the migration must not rewrite them or retroactively score them.

## Minimal implementation sequence and ownership

| Order | Proposed scope | Completion condition |
| --- | --- | --- |
| P0: contract and separation | `scripts/research_memory.py`, new `scripts/hypothesis_stock.py`, idea/novelty contract docs; focused unit tests. | Versioned records, immutable bindings, lock/atomic operations, explicit states, stock-only writes and compatibility dry-run work. No online search or new database dependency. |
| P0: controlled integration | `scripts/next_unattended_loop_step.py`, `scripts/new_experiment.py`, experiment manifest template; replenishment and direction skills; existing lifecycle helpers identified in the writer inventory. | Shared eligibility/projection check, no new-entry legacy bypass or terminal reactivation, idempotent single promotion, one-active guard and existing experiment audits preserved. Enumerate writers/status transitions before enabling migration. |
| P1: generation/review instructions | Proposed `.agents/skills/stock-research-hypotheses/SKILL.md`, existing branch-selection and novelty skills, `automation/INDEPENDENT_JUDGMENT.md`. | Evidence packet, independent initial assessment, reconciliation record, bounded generation and source canonicalization specified. The proposed new skill must route through scripts. |
| P1: outcomes and evaluation | Existing memory-update path and a prospective comparison plan using current experiment tooling. | Failure/inconclusive evidence linked; evaluation inputs, budgets, outcome criteria and limitations locked before any new model call. |

Implement P0/P1 as one coherent workflow before measuring its scientific benefit;
the ordering supports review, not separate exploratory experiment arms. A future
implementation worker owns only these declared files and required focused tests;
it must list additional queue writers before widening scope. A read-only auditor
then checks the actual implementation. No implementation audit is claimed now.

## Acceptance checks for a future implementation

Reuse existing memory, unattended-loop, scientific-contribution and research-focus
tests. Add behavior tests only where a failure would change admission or evidence.

1. Legacy records remain readable; pre-existing unchanged queue entries retain
   their documented path. Unknown contract versions fail explicitly.
2. A new queue entry without a bound eligible revision fails in both routing and
   creation, including after stripping origin/version fields. Changing the queued
   hypothesis or test while retaining valid revision/review references also fails.
3. Duplicate revision IDs, invalid lineage, cycles and forged content hashes fail.
4. Claim, source, test, review, goal or policy changes invalidate stale bindings.
5. Paper/preprint/code aliases count as one canonical work; canonicalization must
   preserve uncertainty when equivalence cannot be established.
6. Failed/incomplete search, zero comparable hits or unavailable material evidence
   cannot yield eligibility. A negative search result is retained as uncertainty.
7. A known duplicate is retained with its target and rationale. Similar wording
   alone cannot cause automatic rejection of a different discriminating test.
8. Stock-only candidate/review operations leave queue and state byte-identical.
9. Repeated valid promotion yields the same queue ID; a distinct stale revision,
   superseded candidate or second live entry is refused. Legacy same-ID/same-content
   append and terminal-to-selectable restoration are refused; missing legacy
   entries and interrupted retirement fail closed without reactivation.
10. Two simultaneous promotions cannot create duplicate entries or bypass the
    one-active guard; partial writes cannot leave accepted malformed JSON.
11. Review packets omit prior scores/desired verdicts, retain conflicting source
    evidence and require a reason when reconciliation changes an assessment.
    This tests protocol construction, not actual resistance to sycophancy.
12. Rejected/inconclusive evidence and all original revisions remain addressable;
    unavailable Qwen/provider execution produces no fabricated result or fallback.

Run affected tests, repository validation and whitespace checks. Avoid a broad
new infrastructure layer or tests that merely mirror field assignments.

## Prospective evaluation proposal

Compare **current replenishment** with **the complete proposed stock workflow** on
the same predeclared research questions and source access, using the same model,
reasoning setting, per-question resource ceilings and maximum candidate count.
Fix the question set, search/call/token/time limits and exact number of questions
in a later locked experiment plan before execution. They are intentionally not
selected from pilot outcomes in this proposal. Include retrieval and review cost
in the treatment budget; the baseline may use its budget within its current rules.
The existing default that emits one ready item is preserved; cap both arms at one
final nominated candidate per question, while retaining all internal attempts.

Primary endpoint: number of distinct nominated candidate clusters that pass a
blinded, source-grounded human assessment per fixed question set and budget.
Acceptance is conjunctive: a specific difference from the closest work, supported
premises, a plausible mechanism, distinguishable competing predictions and an
executable minimal test. This is **scoped test-worthiness**, not a count of new
scientific discoveries. Review every nomination; no model-generated human labels.

Cluster across both arms before revealing their identity. A shared cluster counts
for each arm that nominated a qualifying instance; never award ownership to the
first arm seen. One cluster counts at most once per arm across the question set.
Report missing/invalid/no-output cases for every question and all adjudication
uncertainty. For unresolved judgments, report accepted/rejected/unknown counts and
best/worst bounds; do not silently discard them. Do not optimize thresholds on
the final assessment set.

Secondary diagnostics: prior-work overlap, duplication, unresolved-evidence rate,
contradiction handling, feasibility, stock coverage and total cost. Do not reward
raw bank size, citation volume, forced disagreement or model novelty scores. A
separate controlled preference-flip check can assess sensitivity to irrelevant
user/agent opinions while preserving the evidence; protocol presence alone is
not proof of reduced sycophancy.

Use historical rediscovery only as a labeled diagnostic. A retrieval time cutoff
does not remove future knowledge from model weights. A prospective track needs
new human assessment and ultimately experiments; no present document can certify
an undiscovered hypothesis. The proposal should advance only if qualified yield
improves without worse unsupported-claim or unresolved-evidence rates under the
locked budgets; report inconclusive comparisons rather than search for a winning
seed, prompt, question subset or rating threshold.

## Risks and deferrals

- Independent models can share blind spots. Preserve source disagreements and
  human uncertainty; model diversity is not an evidence substitute.
- More screening may reduce yield and increase cost. The fixed-budget comparison
  must include those costs and failures, not count only surviving candidates.
- Canonicalization can merge genuinely distinct work; uncertain aliases require
  review. Embedding search and automated semantic merging are deferred.
- Strict admission can impede legacy workflows. The migration report and explicit
  allowlist make the boundary inspectable without rewriting historical evidence.
- No claim is made that these engineering patterns themselves constitute a novel
  scientific contribution. The surveyed systems motivate them; efficacy remains
  untested in this repository.
