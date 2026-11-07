---
name: query-paper-knowledge
description: Query the existing paper graph for a research question when requested; return a compact planning brief.
---

# Query Paper Knowledge

Speak to the human in Japanese; keep files in English outside `human/`.

## Scope

- Start with `paper_knowledge/ENTRYPOINT.md` and the generated brief. The CLI
  reads `graph.json`; open individual notes only to resolve a specific gap.
- Graph queries do not authorize new web research. A requested graph update
  uses `$research-paper-graph` within the user's approved source scope.
- Do not modify main research state, active experiments, datasets, baselines, or
  source code.
- Treat the query pack as advisory prior context, not evidence.

## Procedure

1. Read `paper_knowledge/ENTRYPOINT.md`.
2. Form a query from the current planning question, method, dataset, metric,
   task, and hypothesis terms.
3. Run:

   ```bash
   python3 paper_knowledge/bin/pk.py brief --query "<query>"
   ```

4. Read `paper_knowledge/out/planning_brief.md`.
5. Summarize only compact planning cues:
   - matched node IDs,
   - similar mechanisms or datasets,
   - supported or contradicted claims,
   - missing method/data/metric relations,
   - negative or failed directions that should not be repeated.
6. If the graph is stale or empty, report that and suggest
   `$research-paper-graph`; do not invent graph facts.

## Output

Return a concise Japanese summary with the query, brief path, usable cues, and
unresolved gaps. Do not create, revise, lock, implement, or evaluate an
experiment from this skill.

