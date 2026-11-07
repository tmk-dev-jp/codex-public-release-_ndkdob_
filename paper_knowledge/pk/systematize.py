from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from .brief import detect_gaps
from .markdown import ingest_markdown_path
from .model import Edge
from .store import GraphStore


def systematize(store: GraphStore, notes_path: Path, root: Path, out_path: Path, allow_outside: bool = False) -> int:
    ingested = 0
    if notes_path.exists():
        ingested = ingest_markdown_path(store, notes_path, root=root, allow_outside=allow_outside)
    add_tag_relations(store)
    errors = store.validate()
    if errors:
        raise ValueError("; ".join(errors[:5]))
    store.save()
    write_report(store, out_path, ingested)
    return ingested


def add_tag_relations(store: GraphStore) -> int:
    by_tag: dict[str, list[str]] = defaultdict(list)
    for node in store.nodes.values():
        for tag in node.tags:
            by_tag[tag].append(node.id)
    added = 0
    for tag, node_ids in by_tag.items():
        if len(node_ids) < 2:
            continue
        node_ids = sorted(set(node_ids))
        for index, source in enumerate(node_ids):
            for target in node_ids[index + 1 :]:
                store.add_edge(
                    Edge(
                        source=source,
                        target=target,
                        type="related_by_tag",
                        evidence=f"shared tag: {tag}",
                        confidence=0.4,
                    )
                )
                added += 1
    return added


def write_report(store: GraphStore, out_path: Path, ingested: int) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    gaps = detect_gaps(store, set(store.nodes))
    kinds: dict[str, int] = defaultdict(int)
    for node in store.nodes.values():
        kinds[node.kind] += 1
    lines = [
        "# Paper Knowledge Systematization Report",
        "",
        f"- Ingested Markdown files: {ingested}",
        f"- Nodes: {len(store.nodes)}",
        f"- Edges: {len(store.edges)}",
        "- Node kinds: " + ", ".join(f"{kind}={count}" for kind, count in sorted(kinds.items())),
        "",
        "## Structural Gaps",
        "",
    ]
    lines.extend(gaps or ["- No structural gaps detected."])
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

