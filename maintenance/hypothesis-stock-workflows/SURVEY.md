# Agent workflows for a stock of novel, testable hypotheses

Surveyed on 2026-10-23–24 (Asia/Tokyo); publication cutoff 2026-10-23.
Scope: primary abstracts, official project pages and repository READMEs. No full
papers, payloads or private reference collection were downloaded or inspected.
This is a scoped comparison, not a systematic review or an independent reproduction.

Twelve distinct workflow families are counted below. Versions, a paper and its
code, and closely related extensions count once. Eleven address idea generation,
hypothesis selection or reusable research memory; Agent Laboratory is an adjacent
execution workflow. Five evaluation studies later in this document are not part
of the count. “Undocumented” means not described in the inspected material.

The central recommendation is to strengthen the existing idea bank: save
evidence-bearing candidates, assess them independently, and explicitly promote
one eligible revision into the experiment queue. A missing search result cannot
establish that a hypothesis has never been discovered. Eligibility should mean
worth testing under a recorded search scope, not proven novelty or truth.

## Twelve workflow families

| # | Family and inspected version | Generation and retrieval | Novelty, duplication and stock | Evidence limit and proposed adaptation |
| --- | --- | --- | --- | --- |
| 1 | **Google AI co-scientist / Co-Scientist**. Introduced February 2025; May 2026 official update. [Initial account](https://research.google/blog/accelerating-scientific-breakthroughs-with-an-ai-co-scientist/), [updated workflow](https://deepmind.google/blog/co-scientist-a-multi-agent-ai-partner-to-accelerate-research/), [paper](https://arxiv.org/abs/2502.18864). | Generation, reflection, proximity grouping, tournament ranking, evolution and meta-review iteratively develop proposals. | Reflection examines novelty; proximity groups related proposals. Iteration retains candidates and feedback; cross-session stock management is undocumented. | Expert preferences and selected biomedical validations support particular cases. Tournament wins do not establish novelty. **Adapt:** retain critique and lineage, then select across mechanism groups rather than trust a global score. |
| 2 | **SciAgents**. September 2024. [Abstract](https://arxiv.org/abs/2409.05556), [official code](https://github.com/lamm-mit/SciAgentsDiscovery). | A scientific knowledge graph supplies paths between concepts; scientist and critic roles elaborate hypotheses. An automated variant includes a novelty-search assistant. | The graph stores source knowledge. Persistent candidate admission, stock-wide deduplication and retirement are undocumented. | Bioinspired-materials examples illustrate the method, not a measured prospective discovery rate. **Adapt:** record the source-to-mechanism bridge and its falsifier; a graph connection alone is not a causal explanation. |
| 3 | **ResearchAgent**. April 2024 preprint; February 2025 revision, NAACL 2025. [Abstract](https://arxiv.org/abs/2404.07738), [official code](https://github.com/JinheonBaek/ResearchAgent). | A core paper, academic graph and entity knowledge store support problems, methods and experiment proposals. Review agents guide revision. | Novelty is an evaluation dimension; history supports refinement. Cross-run candidate storage and stock-wide deduplication are undocumented. | Human/model idea-quality judgments do not demonstrate completed discoveries. **Adapt:** keep retrieved knowledge separate from a candidate's revision history and require an explicit difference from the closest work. |
| 4 | **Sakana AI Scientist family**, v1 (August 2024) and v2 (2025), counted once. [v1 project](https://sakana.ai/ai-scientist/), [v2 official code](https://github.com/SakanaAI/AI-Scientist-v2). | Ideas from research contexts pass refinement and literature checks before experiments, writing and review; v2 includes experiment-tree exploration. | v1 describes an accumulating knowledge archive and feedback from previous work. v2 exposes structured idea and experiment records. | v2 workshop acceptance is a publication outcome; it does not validate every generated claim. **Adapt:** preserve failed ideas and experiment outcomes; search failure must not clear the novelty gate. |
| 5 | **HKU AI-Researcher**. May 2025. [Abstract](https://arxiv.org/abs/2505.18705), [official code](https://github.com/HKUDS/AI-Researcher). | Resource collection and filtering feed idea generation, design, implementation and refinement. | Novelty appears in evaluation. Explicit overlap adjudication, cross-run deduplication and a persistent untested-hypothesis stock are undocumented. | Scientist-Bench assessments address end-to-end research outputs, not independently established novelty of every candidate. **Adapt:** distinguish source collection, evidence assessment and admission; citation counts should not confer authority. |
| 6 | **Agent Laboratory**. January 2025; June revision. [Abstract](https://arxiv.org/abs/2501.04227), [official code](https://github.com/SamuelSchmidgall/AgentLaboratory). | Human research ideas lead to literature review, experimentation and reporting with human feedback. | This is an adjacent execution workflow. Standalone novelty adjudication, candidate deduplication and a persistent hypothesis bank are undocumented. | Author evaluations support the usefulness of feedback; they do not establish autonomous hypothesis discovery. AgentRxiv is treated separately below. **Adapt:** record feasibility constraints and downstream outcomes before promoting ideas. |
| 7 | **SciMON**. May 2023 preprint; ACL 2024. [Published abstract](https://aclanthology.org/2024.acl-long.18/), [official code](https://github.com/EagleW/Scientific-Inspiration-Machines-Optimized-for-Novelty). | Background and retrieved inspirations seed ideas, followed by comparison with prior papers and iterative revision. | Novelty-oriented comparison is explicit. Persistent stock and candidate-to-candidate duplicate adjudication are undocumented. | Reported improvements coexist with limits in novelty and technical depth. **Adapt:** store the closest-work comparison with revision ancestry and a bounded stopping rule. |
| 8 | **MOOSE / MOOSE-Chem**, counted once. MOOSE: ACL Findings 2024; Chem: October 2024 preprint, ICLR 2025, October 2025 revision. [MOOSE paper](https://aclanthology.org/2024.findings-acl.804/), [code](https://github.com/ZonglinY/MOOSE), [Chem abstract](https://arxiv.org/abs/2410.07076), [code](https://github.com/ZonglinY/MOOSE-Chem). | Feedback-guided hypothesis development; Chem retrieves and combines inspirations, then ranks candidates. | Intermediate hypotheses and feedback are retained; cross-run duplicate merging and retirement are undocumented. | Chem evaluates recovery of later published findings. Rediscovery and author-reported temporal controls do not prove prospective novelty or freedom from model contamination. **Adapt:** separate generation, evidence screening and ranking, preserving the inspiration chain. |
| 9 | **HypoGeniC / HypoRefine**, counted once. April/October 2024 preprints; inspected revisions December 2024/January 2025. [HypoGeniC](https://arxiv.org/abs/2404.04326), [HypoRefine](https://arxiv.org/abs/2410.17309), [official code](https://github.com/ChicagoHAI/hypothesis-generation). | Examples seed hypotheses; reward-based updating allocates attention. HypoRefine combines literature and data. | Explicit literature, refined and combined hypothesis banks support inference. Literature novelty and semantic duplicate adjudication are undocumented. | Predictive accuracy measures usefulness on tasks, not causal truth or discovery. **Adapt:** store empirical support separately from novelty evidence and retain counterexamples. |
| 10 | **NOVA**. October 2024 preprint; ACL Findings 2025. [Preprint](https://arxiv.org/abs/2410.14255), [published abstract](https://aclanthology.org/2025.findings-acl.1099/), [official code](https://github.com/hflyzju/Nova). | Iterative planning controls external knowledge acquisition. The README describes a paper index and saved final proposals after deduplication. | Diversity and deduplication are explicit; cross-run admission rules and duplicate decision details are undocumented in the inspected material. | Human/automated assessments and tournament results are idea-quality evidence. **Adapt:** preserve retrieval paths and duplicate decisions; do not equate varied wording with distinct mechanisms. |
| 11 | **AgentRxiv**. March 2025. [Abstract](https://arxiv.org/abs/2503.18102), [official project](https://agentrxiv.github.io/). | Research agents publish and retrieve reports through a shared preprint environment, enabling cumulative work. | The durable store contains reports, not principally untested hypotheses. Independent report validation and duplicate-merging rules are undocumented. | Author benchmarks show gains in particular tasks, not the reliability of every report. **Adapt:** reuse accepted outcomes and failures with explicit evidence status; a prior agent report must not silently become verified fact. |
| 12 | **SciPIP**. October 2024; February 2025 revision. [Initial abstract](https://arxiv.org/abs/2410.23166v1), [updated abstract](https://arxiv.org/abs/2410.23166), [official code](https://github.com/cheerss/SciPIP). | Semantic, entity and citation retrieval support literature-derived and model-brainstorming routes. | A paper database and JSON idea outputs are described; cross-run hypothesis admission, retirement and deduplication are undocumented. | Retrieval/idea agreement and model originality assessments are proxies for discovery. **Adapt:** record which retrieval route supports each claim; the repository does not need a new graph database to do this. |

## What evaluation evidence changes in the proposal

These five studies constrain evaluation design; they are not extra workflows.

| Primary source | Relevant evidence | Consequence |
| --- | --- | --- |
| [Can LLMs Generate Novel Research Ideas?](https://arxiv.org/abs/2409.04109), September 2024 | Blinded researcher comparisons found stronger novelty judgments for model ideas alongside lower feasibility and failures of diversity/self-evaluation. | Novelty, testability and feasibility need separate judgments. The generator's self-rating cannot be the acceptance criterion. |
| [HypoBench](https://arxiv.org/abs/2504.11524), April 2025; February 2026 revision | Measures hypothesis utility, generalizability and discovery of known structure across real/synthetic settings. | Record usefulness and counterexamples independently; retrospective recovery is a different endpoint from a new scientific finding. |
| [ExAnte](https://aclanthology.org/2026.eacl-long.72/), EACL March 2026 | Explicit historical cutoffs do not reliably remove models' internalized future knowledge. | Time-filtered retrieval is useful but cannot establish an uncontaminated historical trial. Reserve a prospective assessment and disclose model-training uncertainty. |
| [Is This Idea Novel? / RINoBench](https://aclanthology.org/2026.lrec-1.370/), LREC May 2026 | Plausible explanations do not reliably imply correct novelty judgments against human labels. | Require cited comparisons and independent judgment; a model novelty score is only diagnostic. |
| [AgentIdeaBench](https://arxiv.org/abs/2609.07611), September 2026 preprint | In the authors' evaluation, active exploration improves grounding and several quality dimensions while measured originality remains unchanged. | More retrieval cannot itself count as novelty improvement. Measure the complete proposed workflow against equal resource and output limits. |

## Synthesis and limits

Generation/refinement is common. Explicit hypothesis banks are clearest in the
HypoGeniC family; AI Scientist emphasizes accumulated research knowledge, while
AgentRxiv stores reports. These are different memory objects. The inspected
sources provide less detail about long-term candidate identity, duplicate
adjudication, stale reviews and controlled promotion than about generating ideas.
This is an opportunity for repository engineering, not a claim that no published
system already implements those functions.

The proposed workflow combines bounded inspiration search, falsifiable candidate
records, provenance-aware comparison, independent criticism and controlled
promotion. It does not adopt model tournaments as a scientific truth criterion,
require a new database or infer that adding more agents necessarily improves
novelty. Repository findings are in [REPOSITORY_REVIEW.md](REPOSITORY_REVIEW.md);
the actionable proposal is in [PLAN.md](PLAN.md).
