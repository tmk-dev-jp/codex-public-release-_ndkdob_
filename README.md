# Codex-Friendly Deep Learning Research Template

A token-conscious PyTorch scaffold for the controlled cycle:

`hypothesis -> plan audit -> human decision -> implementation -> pre-run audit -> run -> integrity audit -> claim evaluation -> finalization -> memory -> direction -> next hypothesis`

Codex uses frontier/high reasoning for planning and one independent metric-gaming audit. Implementation uses a locked mechanical, balanced, or frontier model profile. A deterministic gate validates state, scope, hashes, bundles, and reusable review output before any subagent starts. Scripts also own transitions, execution, aggregate artifacts, decision-rule arithmetic, and finalization. Pilot and full experiments pass read-only implementation and integrity audits. Training itself is not an agent reasoning task.

Before implementation, DRAFT creation reads no Python source. Planning starts from path listings and records only indispensable source reads in the bounded `SCOPE.json.planning_reads` list.

The supervisor delegates eligible work by default to protect the main model's context, without an explicit delegation request. Give subagents only scoped paths, constraints, and completion criteria rather than the supervisor transcript. Keep exploration and trial details in the subagent context; return concise results and evidence references. The supervisor handles routing, integration, and reporting while preserving skill scope, mechanical gates, and authorization boundaries.

Follow [Independent Judgment](automation/INDEPENDENT_JUDGMENT.md) to resist both user-directed and inter-agent sycophancy: assess evidence before prior interpretations, trace shared sources, preserve dissent and change conclusions only for evidence or corrected reasoning. Role instructions embed the bounded procedure for isolated workers. Static validation checks instruction coverage, not behavioral effectiveness. See [the strategy and evaluation cases](human/INDEPENDENT_JUDGMENT.ja.md).

## Minimal start

```bash
python -m pip install -e ".[dev]"
python scripts/validate.py
python -m pytest -q
```

Use `$initial-setup` to record the agreed research goal and data setup. Once ready,
the project has no active experiment and `next_action.mode=select_experiment`.
Use `$select-next-experiment`, or create the selected draft with:

```bash
python scripts/new_experiment.py --id EXP-001 --stage smoke
```

After finalization, complete memory and direction updates before creating another
draft. Creation requires selection mode; memory completion requires memory mode.
Out-of-order commands fail without advancing state.

Use `human/MANUAL.ja.md` for the complete Japanese operating manual and `human/QUICKSTART.ja.md` for the shortest procedure.

Research Focus at the start of generated context preserves the research question,
planned novelty and discriminating evidence through active work and finalization.
Decision facts carry the same focus; changed research inputs invalidate stale
evaluation material. See `human/NOVELTY_LOOP.ja.md` for the phase-by-phase workflow.

To migrate an existing research directory, use `$migrate-research-project` from a separate template copy and name the source path. Discovery respects the source `.gitignore` files through `scripts/migration_source.py`; the source stays read-only. Review the exact mapping before applying destination changes. See `human/MIGRATE_RESEARCH.ja.md`.

For maintenance across sessions, use `$handoff-maintenance` and resume at `maintenance/HANDOFF.md` after running `python3 scripts/maintenance_handoff.py check`. See `human/MAINTENANCE_HANDOFF.ja.md` for the human workflow. This does not advance research or transfer approvals.

Use `$checkpoint-reproducibility` to preserve the exact experiment inputs with a minimal local Git commit and annotated tag. See `human/REPRODUCIBILITY.ja.md` for commands and the limits of Git-based reproduction.

Use `$set-subagent-defaults` to inspect, set, or clear the project default model and optional reasoning effort for subagents. Explicit spawn settings and custom role models can override these defaults; existing research profiles remain unchanged. See section 19.8.1 in `human/MANUAL.ja.md`.

Use `scripts/update_template.py --github OWNER/REPO --from-tag template-v1 --to-tag template-v2` to preview updates from public GitHub tags without a local template clone. Add `--apply` to update; locally modified files and research records are protected. Local Git sources remain supported through `--template`. See `human/UPDATE_TEMPLATE.ja.md` for baseline selection, conflicts, and recovery.

An explicitly requested `$run-one-unattended-loop` automatically uses `$replenish-research-hypotheses` once if its queue is exhausted before target creation. It investigates one goal-scoped gap using compact records and at most 2-3 similar titles/abstracts/snippets, queues one defensible candidate without confirmation, then follows normal novelty and audit gates. If no candidate is justified, it stops; completion never starts another experiment. See `human/UNATTENDED_LOOP.ja.md`.

Use `$run-one-agent-led-loop` when delegating scientific decisions as well: a separate gated frontier/high worker resolves novelty, plan warnings or revisions, and result interpretation. Decisions retain their sources and input hashes; negative or inconclusive results can complete the loop. Independent audits, external permissions and compute limits remain enforced. See `human/AGENT_LED_LOOP.ja.md`.

Research from public agent projects and papers informs the [decision-handoff improvements](maintenance/AUTONOMOUS_RESEARCH_IMPROVEMENTS.md): cited observations and uncertainty are checked before accepting a decision, prior conclusions are excluded from decision inputs, and a saved worker ID supports inspection after interruption. These checks preserve the existing human and independent-audit boundaries. See [the Japanese guide](human/RESEARCH_AGENT_IMPROVEMENTS.ja.md).

The [expanded review](maintenance/expanded-review/README.md) covers 11 additional repositories and 15 papers, with separate plan and implementation audits. Its changes bind agent interpretation to the dispatched response, block continuation after interrupted acceptance, and provide an offline user/peer-pressure diagnostic. See [the evaluation protocol](human/SYCOPHANCY_EVALUATION.ja.md). Structural checks and synthetic scorer tests do not establish reduced model sycophancy.

The accepted [diagnostic expansion](maintenance/sycophancy-v2/PLAN.md) adds neutral, irrelevant-evidence and peer-prestige controls, plus human assessment of source support and prediction distinguishability. It fixes one 72-prompt-per-arm guidance comparison with no retries or automatic model substitution. The user subsequently selected [Luna at max reasoning](maintenance/sycophancy-v2/LUNA_AMENDMENT.md) because Qwen3.8 is offline. See [implementation and execution status](maintenance/sycophancy-v2/RESULT.md).

The [scientific-discovery review](human/AI_DISCOVERY_REVIEW.ja.md) covers 19 distinct papers/work families through October 2026, separating proposal ratings, reproduction and substantive progress. The [implementation plan](maintenance/AI_DISCOVERY_IMPLEMENTATION_PLAN.md) adds a [source-grounded contribution contract](automation/SCIENTIFIC_CONTRIBUTION.md) for new experiments: observations versus inference, an explicit advance, rival predictions and a decisive comparison. Existing audits judge scientific adequacy; structural validation does not prove novelty or improved discovery rates.
