# Paper Knowledge Entrypoint

Use this file only when the human explicitly asks to consult the paper
knowledge graph during planning, novelty checks, branch selection, or source
discussion.

## Contract

- Keep this layer advisory. Do not treat graph facts as experiment evidence.
- Do not modify `research/`, `references/`, `experiments/`, `data/`, or `src/`
  from this entry point.
- Do not recursively scan outside `paper_knowledge/` unless the human supplies
  an explicit path and scope.
- Prefer deterministic commands over free-form reading.
- Cite generated brief paths or graph node IDs when using the output.

## Planning-Time Procedure

1. Build a query from the current planning question, dataset, method, metric,
   and hypothesis terms.
2. Run:

   ```bash
   python3 paper_knowledge/bin/pk.py brief --query "<query>"
   ```

3. Read the generated `paper_knowledge/out/planning_brief.md`.
4. Use the result only as prior context:
   - similar papers or methods already recorded,
   - unsupported or contradictory claims,
   - missing dataset, metric, or method coverage,
   - possible novelty gaps.
5. If the human asks to update the graph, use the systematization skill in
   `paper_knowledge/skills/systematize-paper-knowledge/SKILL.md`.

## Main Commands

- `init`: create the empty graph store.
- `add-paper`: add one paper node from explicit metadata.
- `add-edge`: add one typed relation.
- `ingest-markdown`: ingest scoped Markdown notes and wikilinks.
- `ingest-csl`: ingest user-supplied CSL JSON metadata.
- `ingest-bibtex`: ingest user-supplied BibTeX metadata.
- `systematize`: refresh notes, add deterministic relation hints, and write a
  compact report.
- `brief`: write a compact planning brief for a query.
- `validate`: check graph consistency.

