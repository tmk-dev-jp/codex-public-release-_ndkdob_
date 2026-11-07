# Public distribution scope

The public template distributes runtime code, configuration templates, fixtures,
tests, skills and operational guides. Development history is kept locally and
excluded from Git tracking using `.gitignore`.

| Excluded scope | Reason |
| --- | --- |
| `maintenance/*`, except `AGENTS.md` and `TASK.template.json` | Local handoffs, improvement surveys, design plans, audit requests/reports, dispatch records, historical hashes and verification summaries |
| `review/sycophancy/*/` | Generated evaluation runs, raw/encoded logs, frozen manifests and historical source snapshots |
| `human/AI_DISCOVERY_REVIEW.ja.md` | Historical development survey and implementation report |
| `human/HYPOTHESIS_STOCK_WORKFLOWS.ja.md` | Unimplemented development proposal and review history |
| `human/RESEARCH_AGENT_IMPROVEMENTS.ja.md` | Historical improvement survey and verification report |

[PUBLIC_EXCLUSIONS.txt](../../PUBLIC_EXCLUSIONS.txt) lists the previously tracked
files excluded in this cleanup. Future generated files in the scopes above are
also ignored. Ignored files may still exist in a developer's working directory;
use Git-tracked files or `git archive HEAD` for distribution.

The historical Luna and Qwen evaluation directories are not distributed. No past
results or hashes were regenerated. Historical designs, audits and source snapshots
are not required to run a new study and cannot be reverified from this template.
The evaluation guide documents current commands rather than past run outcomes.

`maintenance/AGENTS.md`, `maintenance/TASK.template.json` and the handoff script
remain available. Handoff snapshots are created locally on demand. Research state,
experiment controls, runtime validation, fixtures and tests are unchanged.
