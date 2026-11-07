# Research-agent evidence: current capability checks

Checked 2026-10-22. These four distinct primary papers complement the system
papers in `AI_RESEARCH_LITERATURE_FOUNDATIONS.md` and
`AI_RESEARCH_LITERATURE_RECENT.md`. Scope: official abstracts and publication
metadata only; no full papers, downloads, external code, or benchmark execution.
Results below are authors' reported observations under their evaluation
conditions, not independently reproduced findings. Journal impact factors were
not checked or used as a proxy for scientific correctness.

| ID | Paper and status | Evidence relevant to discovery | Limitation and implementation implication |
| --- | --- | --- | --- |
| B1 | [ScienceAgentBench: Toward Rigorous Assessment of Language Agents for Data-Driven Scientific Discovery](https://proceedings.iclr.cc/paper_files/paper/2025/hash/f12b4df26344f3be803c06b555252efe-Abstract-Conference.html), ICLR 2025, peer-reviewed conference | Evaluates executable scientific tasks drawn from 44 publications. With three attempts, the best tested agent solved 32.4% unaided and 34.3% with expert knowledge. | These are particular models and existing tasks, not a current universal ceiling or a novelty test. Verify execution and task evidence separately from claims of new knowledge. |
| B2 | [Benchmarking AI Agents for Addressing Scientific Challenges Across Scales](https://arxiv.org/abs/2606.12736), 2026-06-10, arXiv preprint; SciAgentArena | Approximately 200 interactive tasks distinguish well-specified analysis from open-ended inquiry; authors report weaknesses in new insights and sustained exploration. | Abstract-level evidence gives no universal effect estimate. Candidate selection needs an unresolved scientific question and an explicit advance criterion, not successful task completion alone. |
| B3 | [DISCERN: Can AI Agents Work Like Scientists and Guide Discovery?](https://arxiv.org/abs/2609.33357), 2026-09-27, arXiv preprint | Tests data integrity, analysis verification, and evidence-grounded hypothesis revision across 203 tasks. Reported perfect-score rates are 60.8%, 34.2%, and 0.6% at the three levels. Counterfactual cases challenge prior expectations. | These are level-specific perfect scores, not overall discovery accuracy. Retain adverse evidence and alternative predictions; never reject valid contradictory evidence solely because it disagrees with literature. |
| B4 | [Into the Unknown: Benchmarking AI agents on open scientific research problems](https://arxiv.org/abs/2610.19159), 2026-10-13, preprint under review | Domain scientists supplied unpublished directions and necessary conditions. None of 135 submissions by nine agents met all conditions; 114 failed an integrity check, often from unperformed work or unsupported numbers. | Results concern the tested tasks and agents; they do not prove discovery impossible. Preregister contribution conditions, preserve source/artifact provenance, and label untested proposals without claiming discoveries. |

## Synthesis for implementation

The supported engineering direction is to separate proposal quality, operational
validity, and evidence of scientific progress. A new name, plausible mechanism,
better benchmark score, agent consensus, or polished manuscript cannot substitute
for all three. The proposed local change should connect a source-backed gap to
different observable predictions under the candidate and strongest alternative,
then state what a practically or scientifically meaningful advance would require.
This is an inference for workflow design; the papers do not validate this local
implementation or prove it increases discovery rates.

## Search coverage

Queries included AI research agents, scientific discovery, novelty limitations,
2026, ScienceAgentBench, DiscoveryBench, and Nature agentic discovery. Latest
included submission: 2026-10-13. This is a scoped review, not an exhaustive or
systematic literature review. Preprints remain provisional and versions of the
same work must not be counted as independent evidence.
