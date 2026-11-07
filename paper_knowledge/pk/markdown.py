from __future__ import annotations

import re
from pathlib import Path

from .model import Edge, Node, infer_kind
from .store import GraphStore


WIKILINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")
TAG_RE = re.compile(r"(?<!\w)#([A-Za-z0-9][A-Za-z0-9_\-/.]*)")
DIRECTIVE_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)::\s*(\S+)(?:\s+(.*))?$")

DIRECTIVE_EDGE_TYPES = {
    "cites",
    "supports",
    "contradicts",
    "extends",
    "uses_method",
    "uses_dataset",
    "reports_metric",
    "addresses_task",
    "links_to",
}


def ingest_markdown_path(store: GraphStore, path: Path, root: Path, allow_outside: bool = False) -> int:
    path = path.resolve()
    root = root.resolve()
    if not allow_outside and not is_relative_to(path, root):
        raise ValueError(f"path is outside paper_knowledge; pass --allow-outside explicitly: {path}")
    files = [path] if path.is_file() else sorted(path.rglob("*.md"))
    count = 0
    for file_path in files:
        if file_path.name.startswith("."):
            continue
        ingest_markdown_file(store, file_path)
        count += 1
    return count


def ingest_markdown_file(store: GraphStore, path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    metadata, body = split_frontmatter(text)
    node_id = metadata.get("id") or f"note:{slugify(path.stem)}"
    kind = metadata.get("kind") or infer_kind(node_id)
    title = metadata.get("title") or path.stem.replace("_", " ").replace("-", " ").title()
    tags = parse_list(metadata.get("tags", "")) + sorted(set(TAG_RE.findall(body)))
    node = Node(
        id=node_id,
        kind=kind,
        title=title,
        aliases=parse_list(metadata.get("aliases", "")),
        tags=tags,
        source={"type": "markdown", "path": str(path)},
        metadata={key: value for key, value in metadata.items() if key not in {"id", "kind", "title", "aliases", "tags"}},
        summary=first_paragraph(body),
    )
    store.add_node(node)
    for target, alias in WIKILINK_RE.findall(body):
        target_id = normalize_target(target)
        store.ensure_node(target_id, alias or target)
        store.add_edge(Edge(source=node_id, target=target_id, type="links_to", evidence=f"wikilink in {path.name}", source_ref=str(path)))
    for line in body.splitlines():
        match = DIRECTIVE_RE.match(line)
        if not match:
            continue
        edge_type, target, evidence = match.groups()
        if edge_type not in DIRECTIVE_EDGE_TYPES:
            continue
        target_id = normalize_target(target)
        store.ensure_node(target_id)
        store.add_edge(
            Edge(
                source=node_id,
                target=target_id,
                type=edge_type,
                evidence=(evidence or f"directive in {path.name}").strip(),
                confidence=0.7,
                source_ref=str(path),
            )
        )


def split_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 4)
    if end == -1:
        return {}, text
    raw = text[4:end].strip()
    body = text[end + 4 :].lstrip()
    metadata: dict[str, str] = {}
    for line in raw.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip().strip('"')
    return metadata, body


def parse_list(value: str) -> list[str]:
    if not value:
        return []
    parts = re.split(r"[;,]", value)
    return [part.strip() for part in parts if part.strip()]


def normalize_target(target: str) -> str:
    target = target.strip()
    if ":" in target:
        prefix, rest = target.split(":", 1)
        return f"{prefix.strip()}:{slugify(rest)}"
    return f"term:{slugify(target)}"


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "unknown"


def first_paragraph(body: str) -> str:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", body) if part.strip()]
    if not paragraphs:
        return ""
    paragraph = re.sub(r"\s+", " ", paragraphs[0])
    return paragraph[:600]


def is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False

