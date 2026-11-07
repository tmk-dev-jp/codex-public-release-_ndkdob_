---
name: discuss-research-theme
description: Discuss and narrow an initial research theme with the user before project setup.
---

# Discuss Research Theme

Speak to the human in Japanese and explain unfamiliar research terms briefly.

## Procedure

1. Read `research/CONTEXT.md`; require setup with no active experiment. Route later-direction work with completed evidence to `$select-research-branch`.
2. Ask at most five questions about the desired decision, interests and exclusions, obtainable data, compute and time limits, and novelty-versus-certainty preference. Do not require a metric or model choice.
3. Separate confirmed facts, assumptions, and unresolved constraints.
4. Propose two to four themes. Give each theme's research decision, coherent claim, sufficient evidence and scale, feasibility, novelty uncertainty, failure mode and stop condition. Distinguish a readiness check from the complete study.
5. Reject or repair themes that are too broad, method-first, untestable, simple replay, infeasible with obtainable data, or over budget.
6. Compare themes qualitatively by decision relevance, falsifiability, feasibility, novelty potential, and time to evidence. Do not invent numeric scores or claim novelty.
7. Recommend only when the tradeoff is clear, then ask the human to choose, combine, revise, or defer. Never select silently.
8. After explicit agreement, return a decision packet: title, question, decision, scope, claim, falsifier, first smoke objective, data needs, baseline category, metric candidates, resource limit, novelty uncertainty, stop rule, and unresolved items.
9. Route the next turn to `$initial-setup` if data or source facts remain unresolved; otherwise route to `$define-research-intent`.

## Boundaries

- Do not edit files or state, or create a queue item or experiment.
- Do not search or read sources. If literature evidence is needed, propose a separate scoped `$research-paper-graph` or `$scan-research-landscape` turn and stop.
- Do not choose a baseline result, metric threshold, architecture, or novelty claim without evidence.
- Do not invoke another Skill in the same turn.
