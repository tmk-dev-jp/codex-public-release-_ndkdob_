Verdict: **REVISE**

All six frozen file hashes match `plan-audit/REQUEST.json`. Two contract gaps should be resolved before calling the proposal implementation-ready.

1. **Medium — `PLAN.reviewed.md:120–131` — Queue contents are not explicitly bound to the reviewed claim.**  
   Promotion records the revision hash and review hash, but the proposed shared predicate does not expressly require the queue’s scientific fields to match that revision. A queue hypothesis or method could therefore change while retaining valid revision references, under a literal implementation of this specification.  
   **Fix:** Define one deterministic projection from the eligible revision to the scientific queue fields, and require routing and creation to verify that projection. Alternatively, bind an immutable admission payload containing those fields. Specify which operational fields may subsequently change. Add a test that modifies the queued hypothesis/test while preserving all revision and review bindings and expects rejection.

2. **Medium — `PLAN.reviewed.md:134–143` — The legacy allowlist cannot alone establish continuous eligibility.**  
   A static manifest of IDs and content hashes cannot distinguish an original entry from a removed entry subsequently reintroduced with the same ID and contents. This conflicts with the promise that removed IDs do not regain grandfathered status. Excluding `status` also leaves the allowed lifecycle changes unspecified; the proposal does not establish how terminal legacy entries avoid renewed admission through status changes. These are specification gaps, not findings about uninspected code.  
   **Fix:** Define the legacy lifecycle explicitly. A minimal option is to retain legacy entries permanently, prohibit replacement/removal, and enforce permitted status transitions through existing lifecycle helpers. If removal remains supported, record irreversible retirement under the writer lock. Test same-ID/same-content reintroduction and attempted restoration of a terminal entry to a selectable status.

The source-to-recommendation logic is otherwise appropriately qualified: twelve distinct families are identified, Agent Laboratory is labeled adjacent, undocumented capabilities are not described as absent, and novelty scores, missing hits and agent agreement are not treated as discoveries. The evaluation proposal controls resources and nominations, retains uncertain outcomes and distinguishes protocol compliance from demonstrated resistance to sycophancy.

Scope/limits: read-only review of the frozen proposal, survey, repository summary and two retained research summaries, plus repository instructions and the required independent-judgment policy; within the 750-line budget. No Python, live research payloads, external source re-verification, implementation inspection or edits. This verdict assesses the proposal; implementation verification remains separate.
