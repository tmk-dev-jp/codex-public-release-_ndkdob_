from __future__ import annotations

import json
from pathlib import Path

from .store import GraphStore


DEFAULT_VIEWER_DATA = Path(__file__).resolve().parents[1] / "viewer" / "graph-data.js"


def write_viewer_data(store: GraphStore, out_path: Path = DEFAULT_VIEWER_DATA) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "1.0",
        "nodes": [node.to_dict() for _, node in sorted(store.nodes.items())],
        "edges": [edge.to_dict() for edge in store.edges],
        "counts": {
            "nodes": len(store.nodes),
            "edges": len(store.edges),
        },
    }
    text = json.dumps(payload, indent=2, sort_keys=True).replace("</", "<\\/")
    out_path.write_text(f"window.PAPER_KNOWLEDGE_GRAPH = {text};\n", encoding="utf-8")

