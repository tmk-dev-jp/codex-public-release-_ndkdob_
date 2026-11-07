# Related Work Notes

These are design references, not vendored code.

- Obsidian uses local Markdown files and note links as a graph-friendly authoring
  model. This project mirrors the lightweight Markdown and wikilink idea while
  keeping the canonical store in JSON.
- Foam is a Markdown personal knowledge management system with backlinks, tags,
  and graph-style navigation. This project adopts the file-first and link-first
  pattern, but keeps execution dependency-free.
- Obsidian citation workflows connect BibTeX or CSL JSON metadata to literature
  notes. This project supports small CSL JSON and BibTeX imports so paper
  metadata can enter the graph without requiring a specific editor.
- Zotero Cita focuses on citation relations and citation-network visualization.
  This project keeps citation edges as typed graph facts such as `cites`,
  `extends`, `supports`, and `contradicts`.
- OpenAlex and Semantic Scholar expose paper metadata and citation graphs via
  APIs. This project does not call network APIs directly by default; users can
  export scoped JSON externally and import it with explicit approval.

Consulted entry points:

- https://obsidian.md/
- https://github.com/foambubble/foam
- https://github.com/hans/obsidian-citation-plugin
- https://github.com/diegodlh/zotero-cita
- https://docs.openalex.org/

