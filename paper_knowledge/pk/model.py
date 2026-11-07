from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


ALLOWED_NODE_KINDS = {
    "paper",
    "claim",
    "method",
    "dataset",
    "metric",
    "task",
    "term",
    "note",
}

ALLOWED_EDGE_TYPES = {
    "cites",
    "supports",
    "contradicts",
    "extends",
    "uses_method",
    "uses_dataset",
    "reports_metric",
    "addresses_task",
    "links_to",
    "related_by_tag",
}


@dataclass
class Node:
    id: str
    kind: str
    title: str
    aliases: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    source: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "title": self.title,
            "aliases": self.aliases,
            "tags": self.tags,
            "source": self.source,
            "metadata": self.metadata,
            "summary": self.summary,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Node":
        return cls(
            id=str(data["id"]),
            kind=str(data.get("kind", "term")),
            title=str(data.get("title", data["id"])),
            aliases=[str(item) for item in data.get("aliases", [])],
            tags=[str(item) for item in data.get("tags", [])],
            source=dict(data.get("source", {})),
            metadata=dict(data.get("metadata", {})),
            summary=str(data.get("summary", "")),
        )


@dataclass
class Edge:
    source: str
    target: str
    type: str
    evidence: str = ""
    confidence: float = 0.5
    source_ref: str = ""

    def key(self) -> tuple[str, str, str, str]:
        return (self.source, self.target, self.type, self.evidence)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "type": self.type,
            "evidence": self.evidence,
            "confidence": self.confidence,
            "source_ref": self.source_ref,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Edge":
        return cls(
            source=str(data["source"]),
            target=str(data["target"]),
            type=str(data.get("type", "links_to")),
            evidence=str(data.get("evidence", "")),
            confidence=float(data.get("confidence", 0.5)),
            source_ref=str(data.get("source_ref", "")),
        )


def infer_kind(node_id: str) -> str:
    if ":" in node_id:
        prefix = node_id.split(":", 1)[0]
        if prefix in ALLOWED_NODE_KINDS:
            return prefix
    return "term"

