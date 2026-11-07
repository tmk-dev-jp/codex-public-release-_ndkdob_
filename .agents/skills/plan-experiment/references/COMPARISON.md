# One Hypothesis, Several Runs

Use only when the core hypothesis needs a jointly evaluated comparison. A single-run config remains valid. A comparison is one experiment and one approval, with sequential child runs, not a new hypothesis or Agent per run.

Copy `experiments/templates/COMPARISON.json` into the existing config's `comparison` field and fill it before locking. Keep the hypothesis in `EXPERIMENT.md`; its existing plan hash binds the whole design.

- `arms`: named systems, each with its role in the core claim, a complete model config and optional loss. All other training settings are shared. Do not invent a second method unrelated to the claim.
- `conditions`: necessary data-parameter changes, applied identically to every arm. Dataset name, split procedure, preprocessing implementation and evaluation code remain shared. Explain the relevance of each condition.
- `seeds`: distinct, preregistered training seeds. Every arm uses every seed in every condition. `data.seed` is fixed across training repeats; if omitted, the parent experiment seed is used. This does not establish generalization across independently sampled datasets.
- `primary`: exactly one candidate/reference contrast. Set the parent `experiment.baseline_id` to null; the reference is run within this experiment, never silently reused from incompatible historical results.
- `aggregation`: `paired_mean`, equal weight over the locked conditions and seeds. Other arms are reported against the same reference for interpretation, not selected as replacement winners. State condition-specific expectations and alternative-explanation checks in the plan. Threshold arithmetic on the primary mean is not proof of the core claim.
- `max_total_batches`: explicit cap covering sanity plus every run's training, validation and test batches. Required bound is `arms * conditions * seeds * (1 + epochs * (max_train_batches + max_validation_batches) + test.max_batches)`. Per-run limits must be finite, including full stage. State's `max_comparison_runs` defaults to 24; existing stage limits and full approval still apply.

All declared cells are required. Do not enumerate speculative combinations or pad the design to reach a count. One condition and one seed are allowed when justified. Nice-to-have work belongs in later plans. Explain independent replication versus repeated measurement, essential controls, total cost and what missing evidence would prevent a conclusion.

The existing plan auditor reviews the whole comparison once. Scripts check shapes, identities, budgets, completeness, hashes and arithmetic. Evaluate all arms and conditions together; no post-hoc dropping, metric substitution, or automatic retry. Failed runs retain their artifacts and stop the experiment. Repair must not overwrite collected evidence or pool different code versions. A changed core hypothesis requires a new plan, not another cell.

References: [ARIS experiment-plan](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep/blob/main/skills/experiment-plan/SKILL.md), [K-Dense experimental-design](https://github.com/K-Dense-AI/scientific-agent-skills/blob/main/skills/experimental-design/SKILL.md). Reuse the claim/run distinction, not their automatic deployment or retry policies.
