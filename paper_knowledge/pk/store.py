from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .model import ALLOWED_EDGE_TYPES, ALLOWED_NODE_KINDS, Edge, Node, infer_kind


DEFAULT_STORE = Path(__file__).resolve().parents[1] / "graph" / "graph.json"


class GraphError(ValueError):
    pass


class GraphStore:
    def __init__(self, path: Path = DEFAULT_STORE) -> None:
        self.path = path
        self.nodes: dict[str, Node] = {}
        self.edges: list[Edge] = []

    @classmethod
    def load(cls, path: Path = DEFAULT_STORE) -> "GraphStore":
        store = cls(path)
        if not path.exists():
            return store
        data = json.loads(path.read_text(encoding="utf-8"))
        for node_id, node_data in data.get("nodes", {}).items():
            node_data = dict(node_data)
            node_data.setdefault("id", node_id)
            store.nodes[node_id] = Node.from_dict(node_data)
        store.edges = [Edge.from_dict(item) for item in data.get("edges", [])]
        return store

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "schema_version": "1.0",
            "updated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "nodes": {node_id: node.to_dict() for node_id, node in sorted(self.nodes.items())},
            "edges": [edge.to_dict() for edge in self.edges],
        }
        self.path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def add_node(self, node: Node) -> None:
        validate_node(node)
        existing = self.nodes.get(node.id)
        if existing is None:
            self.nodes[node.id] = node
            return
        existing.title = node.title or existing.title
        existing.kind = node.kind or existing.kind
        existing.aliases = merge_list(existing.aliases, node.aliases)
        existing.tags = merge_list(existing.tags, node.tags)
        existing.source.update({k: v for k, v in node.source.items() if v not in ("", None)})
        existing.metadata.update({k: v for k, v in node.metadata.items() if v not in ("", None, [])})
        if node.summary:
            existing.summary = node.summary

    def ensure_node(self, node_id: str, title: str = "") -> Node:
        if node_id in self.nodes:
            return self.nodes[node_id]
        node = Node(id=node_id, kind=infer_kind(node_id), title=title or node_id)
        self.add_node(node)
        return node

    def add_edge(self, edge: Edge) -> None:
        validate_edge(edge)
        self.ensure_node(edge.source)
        self.ensure_node(edge.target)
        if edge.key() not in {item.key() for item in self.edges}:
            self.edges.append(edge)

    def validate(self) -> list[str]:
        errors: list[str] = []
        for node in self.nodes.values():
            try:
                validate_node(node)
            except GraphError as exc:
                errors.append(str(exc))
        for edge in self.edges:
            try:
                validate_edge(edge)
            except GraphError as exc:
                errors.append(str(exc))
            if edge.source not in self.nodes:
                errors.append(f"missing source node for edge: {edge.source}")
            if edge.target not in self.nodes:
                errors.append(f"missing target node for edge: {edge.target}")
        return errors

    def as_dict(self) -> dict[str, Any]:
        return {
            "nodes": {node_id: node.to_dict() for node_id, node in self.nodes.items()},
            "edges": [edge.to_dict() for edge in self.edges],
        }


def merge_list(left: list[str], right: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in left + right:
        normalized = str(item).strip()
        if normalized and normalized not in seen:
            result.append(normalized)
            seen.add(normalized)
    return result


def validate_node(node: Node) -> None:
    if not node.id or ":" not in node.id:
        raise GraphError(f"node id must be namespaced: {node.id}")
    if node.kind not in ALLOWED_NODE_KINDS:
        raise GraphError(f"unsupported node kind for {node.id}: {node.kind}")


def validate_edge(edge: Edge) -> None:
    if edge.type not in ALLOWED_EDGE_TYPES:
        raise GraphError(f"unsupported edge type: {edge.type}")
    if not 0.0 <= edge.confidence <= 1.0:
        raise GraphError(f"edge confidence out of range: {edge.confidence}")

