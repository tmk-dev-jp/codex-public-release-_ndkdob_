# Recent agent-science literature: discovery and implementation implications

Verified 2026-10-22. Scope: public abstracts, publisher metadata and official summaries; no PDF downloads, OCR, supplementary materials or systematic full-paper review. Search snippets sometimes expose body text; conclusions below use abstracts/metadata only. This is a maintenance evidence note, not an experiment approval. Eight distinct work families; earlier preprints and later journal versions count once. Venue prestige is descriptive, not evidence of correctness. No journal impact factors were inferred.

## 1. The AI Scientist family

**Latest work:** Lu et al., *Towards end-to-end automation of AI research*, Nature 651, 914–919; published 2026-03-25, peer-reviewed research article. [Publisher](https://www.nature.com/articles/s41586-026-10265-5).

**Version lineage:** *The AI Scientist: Towards Fully Automated Open-Ended Scientific Discovery*, preprint 2024-08-12 ([abstract](https://arxiv.org/abs/2408.06292)); *The AI Scientist-v2: Workshop-Level Automated Scientific Discovery via Agentic Tree Search*, preprint 2025-04-10 ([abstract](https://arxiv.org/abs/2504.08066)). These are related system stages, not three independent confirmations.

**Mechanism/evidence:** Agents generate ideas, implement and run experiments, analyze results and prepare/review manuscripts. The latest abstract compares template-guided and template-free agentic search. A generated paper passed first-round workshop peer review; the workshop acceptance rate was 70%. The v2 abstract reports one of three submissions meeting acceptance criteria.

**Assessment:** Evidence supports feasibility of bounded computational research automation. Workshop acceptance and model review scores do not establish a major new discovery or independent replication. **Reusable implication:** explicitly separate execution success, external review and validated scientific contribution. Require an identifiable advance over closest work and a discriminating experiment before promoting a hypothesis. A prospectively evaluated portfolio with retained failures and independent replication would strengthen the discovery claim.

## 2. Co-Scientist

**Latest work:** Gottweis et al., *Accelerating scientific discovery with Co-Scientist*, Nature 655, 487–496; published 2026-05-19, version of record 2026-07-01, peer-reviewed. [Publisher](https://www.nature.com/articles/s41586-026-10644-y). Earlier *Towards an AI co-scientist*, preprint 2025-02-26 ([abstract](https://arxiv.org/abs/2502.18864)), is the same work family.

**Mechanism/evidence:** Goal-conditioned agents generate, critique, rank and evolve literature-grounded hypotheses. The journal abstract reports drug-repurposing and combination-therapy candidates for acute myeloid leukaemia validated in vitro, plus applications to target discovery and antimicrobial-resistance mechanisms. The earlier abstract reports organoid validation and recapitulation of unpublished findings.

**Assessment:** Experimental validation is stronger evidence than preference scores; rediscovering an unpublished result is a distinct achievement from originating a new scientific claim. These are author-reported studies, not independent replications of the whole system. Tournament ratings remain an internal prioritization signal. **Reusable implication:** maintain the literature gap, underlying assumptions, strongest rival explanation and decisive external test for every candidate; preserve rejected alternatives. Prospective blinded comparisons against equally resourced scientist/agent baselines would clarify incremental discovery value.

## 3. Agent Laboratory

Schmidgall et al., *Agent Laboratory: Using LLM Agents as Research Assistants*, Findings of EMNLP 2025, November 2025, pp. 5977–6043; peer-reviewed proceedings. [ACL Anthology](https://aclanthology.org/2025.findings-emnlp.320/). Initial preprint 2025-01-08 ([abstract](https://arxiv.org/abs/2501.04227)).

**Mechanism/evidence:** Takes a human-provided idea through literature review, experiments and reporting, allowing feedback between stages. Authors report better outcomes with human involvement and an 84% expense reduction relative to previous autonomous methods; researchers participated in assessments.

**Assessment:** Directly relevant to executing and testing ideas, but the human supplies the initiating idea. The abstract does not demonstrate independently originating a novel discovery. Cost and research-quality claims are study-specific and not independently verified here. **Reusable implication:** preserve explicit idea provenance and intervention history; distinguish human-originated hypotheses from agent proposals. Reuse phase artifacts and feedback checkpoints without treating human approval as scientific evidence. Independent prospective assessments of novelty and matched-budget results would strengthen claims of scientific advance.

## 4. Kosmos

Mitchener et al., *Kosmos: An AI Scientist for Autonomous Discovery*, arXiv preprint 2025-11-04; v2 2025-11-05. [Abstract and metadata](https://arxiv.org/abs/2511.02824). No peer-reviewed venue verified in this scoped search.

**Mechanism/evidence:** An objective and dataset initiate cycles of literature search, hypothesis generation and data analysis; a shared structured world model preserves coherence. Authors report seven highlighted discoveries: three reproductions of inaccessible preprinted/unpublished findings and four claimed new contributions. They report independent scientists judged 79.4% of statements accurate, and collaborator estimates of six months' equivalent work per run.

**Assessment:** Traceability and multi-cycle memory are useful; the remaining inaccurate statements and selected case studies limit reliability claims. Collaborator time estimates are not measured causal productivity gains, and statement accuracy is not discovery validity. The independent ratings are reported within the same source, not a separate replication. **Reusable implication:** connect every claim to code/data or primary sources, preserve unresolved contradictions across cycles, distinguish reproduction from new discovery, and validate new claims on held-out evidence. Representative prospective evaluation would change confidence more than more generated code or papers.

## 5. Biomni

Huang et al., *Autonomous biomedical research with an artificial intelligence agent*, Science 393(6813), eadz4351, 2026; peer-reviewed. [Publisher abstract](https://spj.science.org/doi/abs/10.1126/science.adz4351?af=R), [PubMed metadata and abstract](https://pubmed.ncbi.nlm.nih.gov/42424436/). Current PubMed lists 2026-08-20; an indexed ahead-of-print record lists 2026-07-09. Treat these as version/date metadata rather than different papers. Earlier *Biomni: A General-Purpose Biomedical AI Agent*, bioRxiv 2025 ([record](https://www.biorxiv.org/content/10.1101/2025.05.30.656746v1.article-info)).

**Mechanism/evidence:** An action-discovery agent builds a biomedical tool environment; retrieval-guided planning and code execution compose workflows. The abstract reports heterogeneous task benchmarks and cases involving multimodal data, protein stability, laboratory instruments and testable protocols.

**Assessment:** Strong relevance to executable experiment planning and tool access; benchmark success and protocol generation alone do not prove new scientific knowledge. The abstract does not quantify independent discovery replication. **Reusable implication:** ground experiment feasibility in available validated tools and inputs; preserve the scientific question separately from workflow completion. A measured, independently validated new mechanism or effect beyond existing methods would support a stronger discovery claim.

## 6. Robin

Ghareeb et al., *A multi-agent system for automating scientific discovery*, Nature 655, 497–505; published 2026-05-19, version of record 2026-07-01, peer-reviewed. [Publisher](https://www.nature.com/articles/s41586-026-10652-y). Earlier *Robin: A multi-agent system for automating scientific discovery*, preprint 2025-05-19 ([abstract](https://arxiv.org/abs/2505.13400)).

**Mechanism/evidence:** Literature-search and data-analysis agents propose experiments, interpret results and update hypotheses in a laboratory feedback loop. The preprint abstract describes ripasudil as a candidate for dry age-related macular degeneration and a follow-up RNA-seq experiment yielding an ABCA1 mechanistic hypothesis. The journal abstract explicitly calls the approach semi-autonomous.

**Assessment:** A tested candidate plus evidence-driven follow-up is more directly about discovery than manuscript production. Candidate activity does not establish clinical efficacy, and a mechanistic association does not establish causality. General discovery yield cannot be inferred from one application. **Reusable implication:** require each follow-up to state what new observation changes the hypothesis and which competing mechanism it distinguishes. An independently replicated effect and mechanism-specific intervention would strengthen the advance claim; repeated agent agreement would not.

## 7. AutoResearchClaw

Liu et al., *AutoResearchClaw: Self-Reinforcing Autonomous Research with Human-AI Collaboration*, arXiv preprint 2026-05-19, v2 2026-05-23. [Abstract and metadata](https://arxiv.org/abs/2605.20025). No peer-reviewed venue verified.

**Mechanism/evidence:** Debate supports hypothesis generation and analysis; pivot/refine decisions respond to failed experiments; reporting checks and cross-run memory target repeated errors. Authors report a 54.7% advantage over AI Scientist-v2 on a 25-topic experiment-stage benchmark and compare seven human-intervention modes.

**Assessment:** This is benchmark evidence, not proof of new scientific discoveries. The abstract does not specify enough measurement detail to reinterpret the 54.7% as a universal productivity gain. Claims that checks prevent fabrication require adversarial validation. **Reusable implication:** record why an observation warrants refinement versus abandoning a hypothesis; carry forward failures with provenance. Never let repair overwrite locked metrics, controls or inconvenient results. Prospective discovery validation and independent falsification tests of reporting safeguards would change the assessment.

## 8. Paper2Agent

Miao et al., *Reimagining research papers as interactive and reliable AI agents*, Nature, published 2026-09-16; peer-reviewed research article. [Publisher](https://www.nature.com/articles/s41586-026-11044-y).

**Mechanism/evidence:** Converts research outputs into interacting agents; the abstract reports reproducing original results, handling novel user queries and collaboration to prioritize a causal gene for psoriasis.

**Assessment:** Reusable validated methods can make cross-paper synthesis executable. Reproducing source outputs is a foundation, not itself a new discovery; prioritizing a causal gene is a candidate hypothesis unless causal validation follows. No independent replication is established by the abstract. **Reusable implication:** distinguish reference-method reuse from the claimed new combination or explanatory insight; test the new claim beyond the original demonstration data. Independent validation of the prioritized biological mechanism would justify stronger language than computational prioritization.

## Synthesis for repository maintenance

The strongest supported pattern is an evidence-linked loop connecting a precise goal, grounded hypothesis, executable discriminating experiment and updated interpretation. Architecture complexity, internal debate, novelty scores, venue prestige and fluent papers are not substitutes for that chain. These papers support implementing safeguards and research artifacts; they do not experimentally validate the safeguards in this repository.

Concrete design implications, inferred from the above evidence:

- Record the proposed knowledge contribution in operational terms: new phenomenon, mechanism, method capability or resolution of an unresolved contradiction. Identify closest work and the specific difference that matters scientifically.
- Keep novelty and truth separate. An unfamiliar idea can be false; a reproduced result can be true without being novel. Search absence supports a bounded novelty assessment, never proof of global priority.
- Require a strongest alternative explanation and an observation that would distinguish it. Tie experimental arms to that contrast, with common controls, retained seeds and representative conditions.
- Preserve source identity, observation provenance, original claim scope and uncertainty. Repeated quotations of the same study remain one evidence source.
- Distinguish candidate generation, feasibility, benchmark improvement, reproduction, external validation and independently replicated advance. Promotion language must match the achieved stage.
- Treat negative results as information about the hypothesis and record why a pivot changes the question. Do not quietly narrow evaluation, replace failed cells or select favorable outcomes.
- Use quantitative gains only within the paper's measurement scope. Abstract-only access leaves study details and causal attribution unresolved; do not port percentages as expectations.

Decisive uncertainty: available summaries favor feasibility and bounded discoveries over a general claim that autonomous agents reliably produce important novel science. The assessment would strengthen with prospectively registered, matched-resource comparisons across representative questions, retained failures, independently assessed novelty, and external replication of scientific effects.
