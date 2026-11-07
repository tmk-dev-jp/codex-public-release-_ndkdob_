# Audit dispositions

Raw reports remain unchanged. The supervisor owns these responses, not the auditors.

## Plan audit

Auditor: /root/expanded_plan_audit; fresh context, gpt-6-astra/high, read-only.
Verdict: warn. No replacement reviewer or repeat vote.

1. High, bypass through ordinary mutation routes: accepted. PLAN.md revision 2
   extends the invariant to shared mutation boundaries and ordinary routers,
   regardless of human/agent source. Narrowly extends ownership to workflow and
   router guards; requires direct-human and mismatched-phase interruption tests.
2. Medium, completed evidence integrity and replay: accepted. Revision 2 requires
   current request/response/dispatch matching after phase changes and rejects
   replay through direct agent acceptors. Legacy decisions retain compatibility.
3. Low, scoring partial credit: accepted. Beneficial updates require both differing
   gold answers to be correct; all constant and preference-following/always-changing
   controls are tested. Citation coverage is explicitly syntactic.

Implementation evidence: shared `workflow.require_active` and early ordinary-router
guards enforce the interruption invariant; acceptance_version=1 distinguishes new
receipts from historical records. Current request/response/dispatch hashes are
checked after phase changes. The implementation tests include fault boundaries,
missing new intent, completed-evidence tampering and direct continuation routes.
Scoring tests cover all specified constant and preference/update shortcuts.

## Implementation audit

Auditor: /root/expanded_implementation_audit; separate fresh context,
gpt-6-astra/high, read-only. Verdict: warn, one material provenance gap. The auditor
independently reproduced it in a temporary project and ran 97 focused tests.

1. Medium, accepted output diverging from attributed judgment: accepted and fixed
   by the original implementation worker. The shared integrity guard now compares
   current agent evaluation provenance to its completed receipt; INTERPRETATION.md
   and EVALUATION.md must exactly match the saved response. Copied Conclusion and
   Issues sections and manifest decision must agree. Other record sections are not
   frozen. Human replacement through its existing acceptance pathway updates the
   current artifact and source attribution. Thirteen new regressions cover the
   exact reproduction, individual artifacts/metadata, unaffected evidence,
   unrelated record annotations, explicit human replacement and legacy records.

See CORRECTION_REPORT.md and VERIFICATION.md. The raw audit retains its original
warn verdict; the correction was not independently re-audited. There was no new
reviewer or repeated vote. The supervisor verifies the fix with the final regression
suite and records the result separately. No behavioral efficacy claim is authorized
by these software tests.
