---
name: research-paper-graph
description: Investigate scoped sources and record sourced notes and relations in the independent paper knowledge graph.
---

# Research Paper Graph

Use this skill to turn an approved research question or source scope into a
compact paper knowledge graph inside `paper_knowledge/`.

## Boundaries

- Work inside `paper_knowledge/` by default.
- Do not modify `research/`, `references/`, `experiments/`, `data/`, `src/`, or
  main experiment state from this skill.
- Treat the graph as prior context, not experiment evidence.
- Use external search only when the human explicitly permits it or the current
  request asks for investigation.
- Do not download papers, clone repositories, OCR PDFs, or read full papers
  unless the human expands scope.
- Prefer abstracts, READMEs, metadata pages, official docs, and user-supplied
  excerpts over broad source reading.
- Store compact facts, source URLs, and typed relations; do not copy long
  passages into notes.

## Workflow

1. Use the note format and commands below. Read
   `paper_knowledge/ENTRYPOINT.md` only for planning-brief integration, or
   `paper_knowledge/HUMAN_ENTRYPOINT.md` for viewer usage questions.
2. Define the investigation scope:
   - query terms,
   - allowed source types,
   - maximum number of sources,
   - approved reading depth,
   - graph update goal.
3. Reuse the user's scope and authorization. For unspecified routine limits,
   state these conservative defaults; ask only if the research question or
   required source access remains unclear:
   - 3 to 5 sources,
   - abstracts, README summaries, and metadata only,
   - no downloads,
   - graph nodes for papers, methods, datasets, metrics, tasks, and claims.
4. Search or inspect only the approved scope.
5. Create scoped Markdown notes in `paper_knowledge/notes/` using:

   ```markdown
   ---
   id: paper:<citekey-or-slug>
   kind: paper
   title: <title>
   year: <year>
   authors: <author>; <author>
   tags: <tag>, <tag>
   url: <source-url>
   ---

   <One compact summary paragraph.>

   uses_method:: method:<slug>
   uses_dataset:: dataset:<slug>
   reports_metric:: metric:<slug>
   addresses_task:: task:<slug>
   supports:: claim:<slug>
   contradicts:: claim:<slug>
   extends:: paper:<slug>
   cites:: paper:<slug>
   ```

6. Run:

   ```bash
   python3 paper_knowledge/bin/pk.py systematize --notes paper_knowledge/notes
   python3 paper_knowledge/bin/pk.py viewer-data
   python3 paper_knowledge/bin/pk.py validate
   ```

7. If the graph is meant to support planning, also run:

   ```bash
   python3 paper_knowledge/bin/pk.py brief --query "<planning query>"
   ```

8. Report the changed note files, source URLs, added node/edge themes, generated
   viewer path, assumptions, and unresolved gaps.

## Relation Guidance

- Use `supports` only for a claim directly supported by the scoped source.
- Use `contradicts` for explicit negative or conflicting evidence.
- Use `extends` when one paper builds on another method or setup.
- Use `cites` only when the citation relation is visible in the approved scope.
- Use `uses_method`, `uses_dataset`, `reports_metric`, and `addresses_task` for
  concrete method, data, metric, and task facts.
- Use `links_to` sparingly for weak topical associations.

## Output

Keep the final response concise and include:

- `paper_knowledge/viewer/index.html` as the human viewer.
- `paper_knowledge/out/planning_brief.md` when generated.
- The number of sources inspected and any scope limits.
- Any graph gaps that should be resolved before relying on the map.
