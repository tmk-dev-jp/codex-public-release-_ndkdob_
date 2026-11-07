# Current repository contracts

Compact supervisor record of the read-only repository explorer's findings.
This is not a verbatim audit report. The explorer inspected scoped contracts and
relevant validator/router clauses; it did not inspect live idea payloads or edit
files. Line references describe the working tree at survey time.

## Existing strengths

- `.agents/skills/replenish-research-hypotheses/SKILL.md:10–16` restricts
  replenishment to no active experiment and selection mode, reuses viable ideas,
  bounds investigation to two or three close sources, and stops after one failed
  investigation. Its new candidate path also creates a ready queue item.
- `.agents/skills/update-research-direction/SKILL.md:19–23` permits at most one
  result-derived idea, requires evidence and a falsifier, and explicitly separates
  storage from queuing. There is already an idea bank; a second store is unnecessary.
- `.agents/skills/select-research-branch/SKILL.md:10–17` favors decision impact,
  excludes replay/policy violations/exploratory grids, and separates selection from
  experiment creation.
- `.agents/skills/query-paper-knowledge/SKILL.md:12–18,32–39` treats a paper-graph
  brief as advisory, not automatically evidence or authority for new searches.

## Enforced contracts and gaps

| Contract | Observed behavior | Consequence for a proposed change |
| --- | --- | --- |
| `scripts/research_memory.py:9–33,114–128` | Idea fields already include hypothesis, rationale, novelty axis, mechanism, failure mode, minimal test and sources. Validation checks required keys, novelty axis, a policy Boolean and a source list. | Extend a versioned contract in the same bank. In inspected clauses, status vocabulary, unique identity, substantive source links, revision lineage and semantic duplication are not enforced. |
| `scripts/research_memory.py:88–92` | Append is implemented through atomic file replacement; no duplicate guard is visible in this operation. | Atomic replacement does not establish multi-writer safety. Add explicit duplicate/revision checks and a repository-level writer lock if concurrent writes are supported. |
| `scripts/research_memory.py:165–180,191–277` | Novelty is experiment-keyed. Proceed requires a claim, queries, two or three source IDs, five facets and contribution evidence. Versioned rules coexist with a legacy path. | Stock screening should be advisory to, and separate from, the existing experiment novelty audit. Canonical works and search uncertainty need explicit representation. |
| `automation/SCIENTIFIC_CONTRIBUTION.md:47–61` | The contribution contract separates observation, inference and discriminating evidence; it acknowledges structural validation cannot establish entailment or priority. | Preserve that distinction. Distinct IDs alone need not represent independent works. A full hash-chain implementation was outside the explorer's scope. |
| `scripts/next_unattended_loop_step.py:36–50,124–142` | Draft/ready/queued items with five strings and no policy flag can be selectable; the inspected predicate does not check idea provenance. Exhaustion allows one replenishment attempt, then blocks. | New stock-origin queue entries need a shared eligibility predicate. Preserve existing legacy behavior intentionally, without allowing new entries to masquerade as legacy. |
| `scripts/new_experiment.py:41–88`; `experiments/templates/MANIFEST.json:7–23` | One active experiment is enforced; initialization records the queue ID and novelty contract. Exact idea revision/hash is not recorded in the inspected initialization. | New stock promotions need a revision binding that both selection and creation recheck. |

## Proposed priorities

1. Separate stock admission from queue promotion; preserve current one-active and
   bounded replenishment rules.
2. Add candidate identity, immutable revisions, typed evidence, scoped novelty
   screening and explicit duplicate relations to the existing bank.
3. Make one script own idempotent promotion of one eligible revision; share its
   validation with the router and experiment creation.
4. Retain uncertainty, failure and rejected candidates rather than treating
   consensus or an empty literature search as success.

Existing tests to extend in a future implementation:
`tests/unit/test_research_memory.py`, `test_unattended_loop.py`,
`test_scientific_contribution.py`, and `test_research_focus.py`.
Useful cases include identity collisions, missing lineage, stale evidence,
stock-only no-op on queue/state, idempotent promotion and legacy compatibility.
Cross-reference enforcement outside the inspected clauses remains unverified.
