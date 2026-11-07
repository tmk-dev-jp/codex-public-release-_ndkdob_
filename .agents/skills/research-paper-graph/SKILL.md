---
name: research-paper-graph
description: Investigate scoped sources to create or update the paper knowledge graph, or refresh its viewer data.
---

# Research Paper Graph

Choose the requested graph operation. Ordinary skill/code maintenance does not need a graph update.

- Investigate sources or write graph notes: follow [the graph workflow](../../../paper_knowledge/skills/research-paper-graph/SKILL.md). It owns source limits, note format, relation rules, and update commands.
- Refresh viewer data from the existing graph: run `python3 paper_knowledge/bin/pk.py viewer-data` and `python3 paper_knowledge/bin/pk.py validate`. Read `paper_knowledge/HUMAN_ENTRYPOINT.md` only for viewer usage.
- Query existing knowledge without new research: use `$query-paper-knowledge`.

Keep writes inside `paper_knowledge/` and facts advisory. Preserve sourced negative findings. Updating the graph does not authorize changing research direction or experiment state. A source-investigation request supplies permission for its scope; downloads, cloning, OCR, and full papers require additional scope.

Finish with inspected sources, changed notes, verification, relevant graph themes or gaps, and `paper_knowledge/viewer/index.html`. Include the planning brief path only when generated. Do not load every route's documents.

