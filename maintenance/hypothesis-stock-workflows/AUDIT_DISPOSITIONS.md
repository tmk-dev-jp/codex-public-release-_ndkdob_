# Disposition of the single plan audit

The read-only auditor reviewed the hash-frozen `PLAN.reviewed.md` and returned
REVISE with two medium findings. `PLAN_AUDIT.md` preserves the returned report.
The supervisor revised `PLAN.md`; no second vote or replacement auditor was used.
These are specification fixes, not implemented or independently retested fixes.

| Finding | Change to the proposal | Required future verification |
| --- | --- | --- |
| Queue content could diverge from the reviewed revision while retaining its references. | Define one deterministic scientific queue projection and immutable admission hash; compare the actual payload during both routing and creation. Enumerate allowed operational changes and reject unknown claim-bearing fields. | Mutate queued hypothesis/test with unchanged valid revision/review references; both consumers must reject. |
| A static legacy allowlist could not prevent reintroduction or terminal reactivation. | Retain legacy entries permanently, reject reuse of every ledger ID, map statuses explicitly, and record irreversible consumption/retirement before dependent transitions. Validate the ledger during selection; interrupted transitions fail closed. State the limit for unobserved manual filesystem rewrites. | Same-ID/same-content insertion, terminal reactivation, missing entries and interrupted retirement must not regain eligibility. |

The revised design adds a small retirement ledger and explicit recovery condition
to the original static-manifest proposal. This is necessary for its no-reactivation
claim. Ordinary new candidate promotion remains a single queue write. The bounded
implementation inventory must identify the existing status/lifecycle helpers
before enabling migration; no helper behavior was assumed from uninspected code.
