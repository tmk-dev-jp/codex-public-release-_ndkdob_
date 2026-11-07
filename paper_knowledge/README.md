# Paper Knowledge

This directory is an independent literature-knowledge layer for the research
template. It stores sparse graph facts about papers, claims, methods, datasets,
metrics, tasks, and concepts without coupling to `research/`, `references/`,
`scripts/`, or `src/`.

The intended entry point for planning-time use is:

- `paper_knowledge/ENTRYPOINT.md` for agent instructions.
- `python3 paper_knowledge/bin/pk.py brief --query "<topic>"` for a compact
  planning brief.

The graph is local, deterministic, and dependency-free. It uses JSON as the
canonical store and Markdown notes as an Obsidian-like authoring surface.

## Design

- Nodes represent papers, claims, methods, datasets, metrics, tasks, terms, and
  notes.
- Edges represent relations such as `cites`, `supports`, `contradicts`,
  `extends`, `uses_method`, `uses_dataset`, `reports_metric`, `addresses_task`,
  `links_to`, and `related_by_tag`.
- Markdown notes can use wikilinks like `[[paper:smith2024]]` and relation
  directives like `uses_method:: method:contrastive-learning`.
- CSL JSON and small BibTeX files can be imported into the graph.
- Planning consumes generated briefs only; it does not mutate research state.

## Quick Start

Create or refresh the store:

```bash
python3 paper_knowledge/bin/pk.py init
```

Ingest local notes:

```bash
python3 paper_knowledge/bin/pk.py ingest-markdown paper_knowledge/notes
```

Run deterministic systematization:

```bash
python3 paper_knowledge/bin/pk.py systematize --notes paper_knowledge/notes
```

Generate a planning brief:

```bash
python3 paper_knowledge/bin/pk.py brief --query "contrastive robustness"
```

Each CLI command prints exactly one final `OK ...` or `ERROR ...` line.

