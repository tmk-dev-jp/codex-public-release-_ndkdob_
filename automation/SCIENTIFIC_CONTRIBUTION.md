# Scientific contribution contract

Use for new novelty checks and planning. A contribution is a claim to test, not
an established discovery. New experiments carry `novelty_contract_version: "1.0"`
in their script-owned manifest. Their `proceed` novelty record needs the object
below, within existing source, plan, response and audit budgets.

## Record

Add `contribution` to the existing novelty JSON object:

- `schema_version`: `"1.0"`.
- `kind`: `discovery`, `method_advance`, `boundary`, or `replication`.
- `source_observations`: 1-3 distinct objects with `source` and `observation`.
  Source identifiers must exactly match the record's `similar_items`. State what
  the inspected source establishes; distinguish an untested condition from an
  established negative result. Repeated versions of one work are not corroboration.
- `inference`: the unresolved question and proposed claim inferred from those facts.
- `advance`: what becomes known or achievable, and why it matters beyond a routine
  extension. A replication supplies supporting evidence, not a new discovery.
- `alternative`: strongest explanation that does not require the claimed advance.
- `candidate_prediction` and `alternative_prediction`: different observable
  outcomes under the same proposed test. Paraphrases of one prediction do not
  constitute a scientific distinction, even if a structural check accepts them.
- `discriminating_test`: the decisive contrast and necessary matched controls.
- `advance_criterion`: a preregistered condition for meaningful progress and an
  outcome that defeats or narrows the claim. Reuse the primary decision rule;
  do not introduce another promotion metric or adapt the rule after results.

Use concise substantive strings, not placeholders. Prioritize an unresolved
phenomenon, mechanism, capability, contradiction or boundary condition. A renamed
method, extra compute, changed dataset, higher score or unfamiliar combination
alone does not explain scientific progress. Negative findings can be progress
when they resolve an important question. Prefer one defensible candidate to a
large proposal grid; preserve the blocking gap if none is justified.

## Carry into the existing plan

| Existing field | Content |
| --- | --- |
| `Rationale` | Separate source observations from the proposed inference. |
| `Novelty check` | Source IDs, contribution kind, substantive advance and uncertainty. |
| `Alternative explanation` | Strongest rival explanation. |
| `Minimum discriminating evidence` | Both predictions, test and necessary controls. |
| `Claim`, decision rule and `Falsifier` | Advance criterion, supported scope and defeating outcome. |

The independent plan audit checks this mapping and scientific adequacy. Full
novelty contents and contract version enter existing audit/decision provenance.
Changes need the ordinary revision and fresh audit route, not a replacement vote.
At evaluation, compare actual observations with the locked predictions and
criterion; keep feasibility, reproduction, gain and supported advance distinct.

## Compatibility and limits

Historical records and manifests without the version remain legacy records;
they are not rewritten or retroactively certified. A supplied contribution is
validated even in a legacy record. Do not remove a new experiment's version to
bypass its requirement. Unknown versions are unsupported. The record validator
checks structure and source membership, not source retrieval, entailment,
worldwide priority or scientific importance. Insufficient scoped evidence uses
`needs_human` or `revise`; 2-3 search hits are not an exhaustive priority search.
