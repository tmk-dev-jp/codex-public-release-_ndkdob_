---
name: systematize-paper-knowledge
description: Deterministically update and query the independent paper_knowledge graph from scoped notes or metadata before research planning.
---

# Systematize Paper Knowledge

Use this skill when the human asks to organize literature knowledge, import
scoped paper metadata, update graph relations, or consult the graph during
research planning.

## Boundaries

- Work only inside `paper_knowledge/` unless the human provides an explicit
  import path and scope.
- Do not modify the main research state, active experiments, datasets, or
  source code.
- Do not download papers, crawl repositories, or read full papers broadly.
- Store compact metadata, claims, and typed relations only.
- Treat generated briefs as advisory context, not evidence.

## Procedure

1. Read `paper_knowledge/ENTRYPOINT.md`.
2. If the graph must be updated from local notes, run:

   ```bash
   python3 paper_knowledge/bin/pk.py systematize --notes paper_knowledge/notes
   ```

3. If the graph must be queried for planning, run:

   ```bash
   python3 paper_knowledge/bin/pk.py brief --query "<query>"
   ```

4. Read `paper_knowledge/out/planning_brief.md` or
   `paper_knowledge/out/systematization_report.md`.
5. Report node IDs, relation types, assumptions, and gaps compactly.

## Output Discipline

The CLI emits one final `OK ...` or `ERROR ...` line. Use generated files for
details.

