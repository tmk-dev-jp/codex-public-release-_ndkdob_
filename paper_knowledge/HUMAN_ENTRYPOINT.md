# Human Viewer Entrypoint

Open the paper knowledge graph viewer at:

```text
paper_knowledge/viewer/index.html
```

Before opening the viewer, refresh the browser data file:

```bash
python3 paper_knowledge/bin/pk.py viewer-data
```

The viewer is a local static application. It reads
`paper_knowledge/viewer/graph-data.js`, visualizes the graph, and supports
search, type filters, edge filters, node details, pan, zoom, and drag.

For a different graph file, use the viewer's local JSON file control. The
expected file shape is the canonical `paper_knowledge/graph/graph.json` format:

```json
{
  "nodes": {
    "paper:example": {
      "id": "paper:example",
      "kind": "paper",
      "title": "Example Paper"
    }
  },
  "edges": [
    {
      "source": "paper:example",
      "target": "method:example",
      "type": "uses_method"
    }
  ]
}
```

