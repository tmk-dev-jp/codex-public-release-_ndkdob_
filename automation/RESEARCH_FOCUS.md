# Keep the Research Question and Novelty in View

Use the generated Research Focus in `research/CONTEXT.md` at each phase handoff.
The question comes from `research/GOAL.md`; experiment details come from the
existing plan fields. Missing values are unresolved facts, never permission to
invent them. Novelty is a hypothesis about contribution, not a verified result.

- Generation: derive the candidate from an unanswered part of the question.
  Name the closest work, its shared mechanism, the proposed difference, and an
  observation that distinguishes that difference from the strongest alternative.
  A different name, dataset or better score alone does not explain a contribution.
  For new novelty records, use [the contribution contract](SCIENTIFIC_CONTRIBUTION.md):
  distinguish source observations from inference and state a substantive advance,
  rival predictions and a decisive test. Replication remains supporting evidence.
- Planning: `Research objective` links the question to this experiment;
  `Novelty check` names closest-source IDs and the proposed difference;
  `Minimum discriminating evidence` states the necessary comparison and an
  outcome that would undermine the novelty claim. Keep all essential controls.
  Carry the contribution kind and advance criterion into these existing fields;
  both candidate and alternative predictions must be observable under the test.
- Implementation and pre-run audit: check that the intervention and controls
  still test that difference. If they cannot, revise the plan through its normal
  gate. Do not quietly substitute an easier question or redefine novelty.
- Evaluation: use `research_focus` in `DECISION_FACTS.json`. In `Supported scope`
  answer the question and say what part of the claimed difference the evidence
  supports. In `Unsupported or missing evidence` say what remains untested,
  contradicted or confounded. A metric gain and a novel contribution are distinct.
  Smoke establishes feasibility only.
- Memory and direction: retain the question, novelty claim and its evidence status
  with experiment/source IDs. Choose the next experiment for the remaining
  discriminating evidence. Narrow or reject unsupported novelty; do not repeat a
  known method as a new contribution. Changes to GOAL require human agreement.

Novelty searches remain bounded to 2-3 close titles/abstracts/snippets. If this
scope cannot justify a difference, record `needs_human` or `revise`; lack of hits
is not proof of novelty. Do not fabricate sources or broaden research scope.
