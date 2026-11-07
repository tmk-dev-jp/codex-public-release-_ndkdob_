from __future__ import annotations

import re
from collections import Counter, defaultdict
from pathlib import Path

from .model import Edge, Node
from .store import GraphStore


def write_planning_brief(store: GraphStore, query: str, out_path: Path, limit: int = 12) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    matches = ranked_nodes(store, query, limit)
    match_ids = {node.id for _, node in matches}
    relations = [edge for edge in store.edges if edge.source in match_ids or edge.target in match_ids]
    gaps = detect_gaps(store, match_ids)
    lines = [
        "# Paper Knowledge Planning Brief",
        "",
        f"- Query: `{query}`",
        f"- Nodes: {len(store.nodes)}",
        f"- Edges: {len(store.edges)}",
        "",
        "## Matched Nodes",
        "",
    ]
    if matches:
        for score, node in matches:
            lines.append(format_node(score, node))
    else:
        lines.append("- No direct graph matches.")
    lines.extend(["", "## Relations", ""])
    if relations:
        for edge in sorted(relations, key=lambda item: (item.source, item.type, item.target))[: max(20, limit * 2)]:
            lines.append(format_edge(edge, store))
    else:
        lines.append("- No relations attached to matched nodes.")
    lines.extend(["", "## Planning Cues", ""])
    lines.extend(planning_cues(store, match_ids))
    lines.extend(["", "## Gaps", ""])
    lines.extend(gaps or ["- No structural gaps detected for matched nodes."])
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def ranked_nodes(store: GraphStore, query: str, limit: int) -> list[tuple[float, Node]]:
    terms = tokenize(query)
    if not terms:
        return []
    scored: list[tuple[float, Node]] = []
    for node in store.nodes.values():
        haystacks = {
            "id": node.id,
            "title": node.title,
            "tags": " ".join(node.tags),
            "summary": node.summary,
            "metadata": " ".join(str(value) for value in node.metadata.values()),
        }
        score = 0.0
        for term in terms:
            if term in tokenize(haystacks["title"]):
                score += 4.0
            if term in tokenize(haystacks["tags"]):
                score += 3.0
            if term in tokenize(haystacks["id"]):
                score += 2.0
            if term in tokenize(haystacks["summary"]):
                score += 1.0
            if term in tokenize(haystacks["metadata"]):
                score += 0.5
        if score > 0:
            scored.append((score, node))
    scored.sort(key=lambda item: (-item[0], item[1].id))
    return scored[:limit]


def detect_gaps(store: GraphStore, match_ids: set[str]) -> list[str]:
    gaps: list[str] = []
    degree = Counter()
    outgoing: dict[str, set[str]] = defaultdict(set)
    incoming: dict[str, set[str]] = defaultdict(set)
    for edge in store.edges:
        degree[edge.source] += 1
        degree[edge.target] += 1
        outgoing[edge.source].add(edge.type)
        incoming[edge.target].add(edge.type)
    selected = match_ids or set(store.nodes)
    for node_id in sorted(selected):
        node = store.nodes[node_id]
        if degree[node_id] == 0:
            gaps.append(f"- `{node_id}` is isolated.")
        if node.kind == "paper":
            missing = []
            if "uses_method" not in outgoing[node_id]:
                missing.append("method")
            if "uses_dataset" not in outgoing[node_id]:
                missing.append("dataset")
            if "reports_metric" not in outgoing[node_id]:
                missing.append("metric")
            if missing:
                gaps.append(f"- `{node_id}` lacks explicit {', '.join(missing)} relation(s).")
        if node.kind == "claim" and not (incoming[node_id] & {"supports", "contradicts"}):
            gaps.append(f"- `{node_id}` has no support or contradiction edge.")
    return gaps[:20]


def planning_cues(store: GraphStore, match_ids: set[str]) -> list[str]:
    if not match_ids:
        return ["- Add scoped notes or metadata before relying on this graph."]
    edge_types = Counter(edge.type for edge in store.edges if edge.source in match_ids or edge.target in match_ids)
    cues = []
    if edge_types:
        cues.append("- Relation coverage: " + ", ".join(f"{key}={value}" for key, value in sorted(edge_types.items())))
    unsupported_claims = [
        node_id
        for node_id in match_ids
        if store.nodes[node_id].kind == "claim"
        and not any(edge.target == node_id and edge.type == "supports" for edge in store.edges)
    ]
    if unsupported_claims:
        cues.append("- Claims needing evidence: " + ", ".join(f"`{item}`" for item in sorted(unsupported_claims)))
    methods = sorted(
        edge.target for edge in store.edges if edge.source in match_ids and edge.type == "uses_method"
    )
    if methods:
        cues.append("- Methods already connected: " + ", ".join(f"`{item}`" for item in methods))
    return cues or ["- Matched nodes have sparse relation coverage."]


def format_node(score: float, node: Node) -> str:
    tags = f" tags={','.join(node.tags)}" if node.tags else ""
    year = node.metadata.get("year", "")
    year_text = f" ({year})" if year else ""
    return f"- score={score:g} `{node.id}` [{node.kind}] {node.title}{year_text}{tags}"


def format_edge(edge: Edge, store: GraphStore) -> str:
    source = store.nodes.get(edge.source)
    target = store.nodes.get(edge.target)
    source_title = source.title if source else edge.source
    target_title = target.title if target else edge.target
    evidence = f" evidence={edge.evidence}" if edge.evidence else ""
    return f"- `{edge.source}` --{edge.type}--> `{edge.target}` ({source_title} -> {target_title}){evidence}"


def tokenize(text: str) -> set[str]:
    return {item for item in re.split(r"[^a-z0-9]+", text.lower()) if item}

