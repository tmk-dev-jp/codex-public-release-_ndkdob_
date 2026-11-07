# Expanded research and independent audits

This maintenance task addresses user-directed and inter-agent sycophancy through
evidence-bound decisions and diagnostic evaluation. Status: complete. Both
independent audits were performed and their findings addressed. Final regression:
544 passed, 2 unchanged sandbox cases deselected, 13 subtests passed; validator
warnings=0. No behavioral efficacy result is available.

- [Survey](SURVEY.md): 11 additional repositories and 11 primary papers, with
  inspected files/sections, limitations and source-to-change inferences.
- [Sycophancy sources](SYCOPHANCY_SOURCES.md): four additional primary papers on
  user preference, peer conformity, identity cues and harmful belief updates.
- [Plan](PLAN.md): three selected changes and explicit acceptance criteria.
- [Independent plan audit](PLAN_AUDIT.md): preserved raw report; verdict warn.
- [Audit dispositions](AUDIT_DISPOSITIONS.md): supervisor responses and fixes.
- [Implementation report](IMPLEMENTATION_REPORT.md): original worker report.
- [Independent implementation audit](IMPLEMENTATION_AUDIT.md): preserved raw report;
  verdict warn, identifying divergent materialized interpretation.
- [Verification](VERIFICATION.md): executed checks and explicit limitations.
- [Correction report](CORRECTION_REPORT.md): original worker's audit-fix report.
- [Japanese evaluation guide](../../human/SYCOPHANCY_EVALUATION.ja.md): protocol,
  commands, response schema and metric definitions.

All 11 repositories and 15 papers are additional to the previous survey. A
repository and its paper count in their respective categories; forks and versions
are not additional items. Seven repositories concern scientific-agent systems;
four are explicitly labeled engineering/evaluation/recovery infrastructure.
The prior excluded repositories are SakanaAI/AI-Scientist-v2,
SamuelSchmidgall/AgentLaboratory and HKUDS/AI-Researcher. Excluded paper IDs are
2504.08066, 2501.04227, 2505.18705, 2511.02824 and 2509.08713.

The survey worker opened the primary sources and bounded code/configuration. No
upstream project was installed or benchmarked. One paper's full text was restricted;
its entry explicitly limits evidence to its abstract and availability sections.
Repository branches were inspected on 2026-10-22 and are not pinned reproductions.

## Audit procedure

The temporary maintenance gate records scoped source hashes and a dispatch marker
before each worker. These records authorize no research execution. The survey,
plan audit, implementation and implementation audit use distinct fresh contexts;
auditors are read-only and do not receive preferred verdicts or the conversation.
There is one worker per phase, no reviewer panel or replacement vote.

Raw survey/audit reports are preserved; source counts and test results are separate
from opinions. Plan revision 2 responds to all three findings. A later correction
does not change the original auditor verdict or imply that an unperformed re-audit
passed. The implementation audit's material finding is corrected through the same
implementation worker and tested; no replacement reviewer or automatic re-audit is
used. Final verification is recorded separately from the raw auditor verdict.
