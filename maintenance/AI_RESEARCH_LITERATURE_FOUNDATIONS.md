# Foundational evidence for research ideation and experiment design agents

Checked 2026-10-22. Maintenance evidence brief; no live experiment state changes.
Seven distinct papers; all have journal or main-conference publication records.
This is a scoped selection of relevant established work, not an exhaustive review
or a claim to cover the newest literature. Venue status is reported directly;
impact factors and citation counts were not used as evidence of scientific validity.

Evidence scope: public primary-source abstracts, publication metadata and publisher
summaries. Search results occasionally exposed additional article text; conclusions
below deliberately use the stated abstract/summary evidence, without a full-paper,
supplement, data or code audit. No PDF download or OCR was performed. Publication
and preprint versions of a work count once. Design implications are our inferences,
not demonstrated improvements to this repository.

## 1. Coscientist

**Paper:** Boiko et al., *Autonomous chemical research with large language models*.
**Date/status:** 20 December 2023; *Nature* 624, 570–578; peer-reviewed journal article.
**Sources:** [Publisher](https://www.nature.com/articles/s41586-023-06792-0),
[NSF research summary](https://www.nsf.gov/science-matters/meet-coscientist-your-ai-lab-partner).

**Agent use:** GPT-4 coordinates literature/documentation search, code and laboratory
automation to design, execute and optimize chemical experiments.
**Evidence:** The abstract reports six task settings and palladium-catalysed
cross-coupling optimization. NSF explicitly describes the complex reaction as
previously invented by humans.
**Assessment/limit:** Strongly relevant to executable experiment planning and feedback;
these inspected summaries do not establish discovery of a new reaction or mechanism.
**Reusable implication:** Record whether a task is reproduction, optimization or
discovery before execution. Require instrument/tool constraints and measured feedback
in plans. Successful execution of a known procedure cannot by itself close a novelty
claim. Evidence of a previously unknown, independently validated phenomenon would
change that assessment.

## 2. ChemCrow

**Paper:** Bran et al., *Augmenting large language models with chemistry tools*.
**Date/status:** 8 May 2024; *Nature Machine Intelligence* 6, 525–535;
peer-reviewed journal article; earlier preprint dated 2023.
**Sources:** [Publisher](https://www.nature.com/articles/s42256-024-00832-8),
[original preprint abstract](https://arxiv.org/abs/2304.05376).

**Agent use:** GPT-4 selects among 18 expert-designed tools for synthesis,
molecular discovery and materials tasks.
**Evidence:** The journal abstract reports synthesis planning/execution for an
insect repellent and three organocatalysts, plus guidance of a novel chromophore
discovery. The preprint abstract flags failure of GPT-4 evaluation to distinguish
incorrect model answers from the tool-assisted system.
**Assessment/limit:** Includes a reported novel output, beyond mere procedure
execution; inspected abstracts do not quantify general discovery reliability or
isolate which agent component caused the advance.
**Reusable implication:** Keep tool observations separate from model interpretation;
evaluate scientific outputs with external measurements and relevant baselines.
Model reviewers' favorable prose is insufficient validation. Controlled replication
and source-level novelty checks would strengthen the discovery assessment.

## 3. The Virtual Lab

**Paper:** Swanson et al., *The Virtual Lab of AI agents designs new SARS-CoV-2 nanobodies*.
**Date/status:** Online 29 July 2025; *Nature* 646, 716–723 (2025);
peer-reviewed journal article.
**Source:** [Publisher abstract and metadata](https://www.nature.com/articles/s41586-025-09442-9).

**Agent use:** A principal-investigator agent directs specialist agents through
research meetings with high-level human feedback. The system designs a pipeline
combining ESM, AlphaFold-Multimer and Rosetta.
**Evidence:** The abstract reports 92 designed nanobodies and experimental testing;
two show improved binding to JN.1 or KP.3 while retaining ancestral spike binding.
**Assessment/limit:** Concrete designed entities plus physical validation provide
stronger discovery evidence than proposal ratings. Binding is not clinical efficacy,
and this case does not establish general autonomous discovery or causal benefit of
every agent role.
**Reusable implication:** A coherent method may combine necessary specialist tools;
lock the final scientific target, baseline and external validation together. Separate
the demonstrated output claim from architecture/component claims. Independent
replication and comparative agent ablations would answer different remaining questions.

## 4. ResearchAgent

**Paper:** Baek et al., *ResearchAgent: Iterative Research Idea Generation over Scientific
Literature with Large Language Models*.
**Date/status:** April 2025; NAACL 2025, Volume 1: Long Papers, 6709–6738;
peer-reviewed main-conference paper; preprint 2024.
**Source:** [ACL Anthology abstract and proceedings metadata](https://aclanthology.org/2025.naacl-long.342/).

**Agent use:** Starts with a core paper, retrieves related publications and concept
entities from graph-based knowledge, then generates problems, methods and experiment
designs. Reviewing agents iteratively refine proposals.
**Evidence:** Abstract reports cross-disciplinary human and model evaluations of
novelty, clarity and validity.
**Assessment/limit:** Directly relevant to proposal construction, but those ratings
do not demonstrate that executing the ideas yields new scientific knowledge.
Human-preference alignment is an evaluation design choice, not truth evidence.
**Reusable implication:** Link each proposed problem, mechanism and test to source
evidence and retain reviewer objections. Bound revisions; do not convert reviewer
consensus into empirical support. Executed, controlled outcomes would change the
assessment from proposal quality to demonstrated progress.

## 5. SciMON

**Paper:** Wang et al., *SciMON: Scientific Inspiration Machines Optimized for Novelty*.
**Date/status:** August 2024; ACL 2024, Volume 1: Long Papers, 279–299;
peer-reviewed main-conference paper.
**Source:** [ACL Anthology abstract and proceedings metadata](https://aclanthology.org/2024.acl-long.18/).

**Agent/workflow use:** Generates natural-language ideas from problems, goals and
experimental context; retrieves prior-work inspirations and revises ideas after
comparison with existing papers.
**Evidence:** Abstract reports that GPT-4 ideas lack novelty and technical depth,
with the proposed methods partially mitigating these weaknesses.
**Assessment/limit:** A useful novelty-grounding workflow, rather than evidence of
general experimental discovery. Retrieval can miss close prior work; textual
distinctness cannot establish nontrivial scientific advance.
**Reusable implication:** Require a closest-work comparison stating the precise
new scientific content and why a routine extension does not explain it. Keep an
unresolved novelty status when sources are insufficient. A discriminating experiment
and verified prior-art separation would strengthen a substantive-progress claim.

## 6. Human evaluation of novel research ideas

**Paper:** Si, Yang and Hashimoto, *Can LLMs Generate Novel Research Ideas? A Large-Scale
Human Study with 100+ NLP Researchers*.
**Date/status:** Preprint 6 September 2024; ICLR 2025 peer-reviewed conference paper.
**Sources:** [Official ICLR proceedings abstract](https://proceedings.iclr.cc/paper_files/paper/2025/hash/ea94957d81b1c1caf87ef5319fa6b467-Abstract-Conference.html),
[preprint abstract and date](https://arxiv.org/abs/2409.04109).

**Agent use:** Evaluates an ideation agent against expert-written NLP ideas with
blind human review and confounder controls.
**Evidence:** Abstract reports higher judged novelty for generated ideas
(p < 0.05), slightly weaker judged feasibility, self-evaluation failures and limited
generation diversity.
**Assessment/limit:** Evidence supports judged idea novelty in the tested setting,
not completed discovery. Authors explicitly identify execution into full projects
as needed to connect ratings with outcomes.
**Reusable implication:** Separate novelty, feasibility and demonstrated advancement;
deduplicate semantically similar candidates and preserve adverse reviews. Do not
promote on self-ranked novelty alone. Controlled execution with scientific outcomes
would resolve the central missing evidence.

## 7. SciAgents

**Paper:** Ghafarollahi and Buehler, *SciAgents: Automating Scientific Discovery Through
Bioinspired Multi-Agent Intelligent Graph Reasoning*.
**Date/status:** Version of record online 18 December 2024; *Advanced Materials*
37(22), 2413523 (2025); peer-reviewed journal article.
**Sources:** [Publisher record](https://advanced.onlinelibrary.wiley.com/doi/10.1002/adma.202413523),
[publisher issue summary](https://advanced.onlinelibrary.wiley.com/toc/15214095/2025/37/22?page=2),
[preprint abstract](https://arxiv.org/abs/2409.05556).

**Agent use:** Combines ontological scientific knowledge graphs, retrieval and
multiple agents to generate and refine hypotheses linking materials concepts.
**Evidence:** Abstract describes bioinspired-material case studies, proposed
mechanisms and cross-domain relationships; the publisher summary describes a
biocomposite with improved properties.
**Assessment/limit:** These summaries do not expose a sufficient measurement/control
protocol to distinguish generated predictions from independently established material
performance. Broad superiority claims remain author claims within this scope.
**Reusable implication:** Label each graph link as source observation, inference or
new hypothesis. A connection across fields requires a testable mechanism and a
measurement capable of refuting it. Access to controlled validation evidence would
change the present uncertainty about actual material discovery.

## Integration implications and unresolved evidence

The strongest reusable distinction is between **new proposal**, **validated new
output**, and **supported scientific explanation or advance**. These are different
claims and should remain different states in planning and evaluation. Publication
prestige, model consensus and polished explanations cannot substitute for the
appropriate evidence. Nor does an unfamiliar combination of existing tools alone
establish a nontrivial scientific contribution.

For hypothesis generation, record: the unresolved question; closest established
work; the proposed mechanism or capability delta; whether this is reproduction,
incremental optimization or a discovery candidate; a plausible ordinary explanation;
and the observation that would distinguish the candidate from that explanation.
Use a small set of distinct, source-grounded candidates rather than a large prompt
grid. Novelty uncertainty must remain visible when retrieval coverage is incomplete.

For experiment planning, connect the alleged advance to a decisive contrast and
appropriate controls. A benchmark gain can support a performance claim; a mechanism,
generalization or discovery claim needs evidence that discriminates that claim from
routine tuning, additional compute, changed data, or known methods. Component-level
causality requires isolating comparisons, while a coherent combined method need not
be fragmented into unrelated experiments.

For evaluation, retain failures and objections, distinguish measured facts from
interpretation, and state what evidence would change the assessment. This review
motivates workflow safeguards; it does not establish their effectiveness. Testing
whether repository changes improve discovery quality would require a separate,
controlled study with an explicitly defined scientific outcome.
