from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .markdown import slugify
from .model import Node
from .store import GraphStore


def ingest_csl_json(store: GraphStore, path: Path) -> int:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        items = [data]
    else:
        items = list(data)
    count = 0
    for item in items:
        if not isinstance(item, dict):
            continue
        node = csl_item_to_node(item, path)
        store.add_node(node)
        count += 1
    return count


def csl_item_to_node(item: dict[str, Any], path: Path) -> Node:
    item_id = str(item.get("citation-key") or item.get("id") or item.get("DOI") or item.get("title") or "unknown")
    title = str(item.get("title") or item_id)
    year = extract_csl_year(item)
    authors = [format_csl_name(author) for author in item.get("author", []) if isinstance(author, dict)]
    tags = [str(tag) for tag in item.get("keyword", [])] if isinstance(item.get("keyword"), list) else []
    return Node(
        id=f"paper:{slugify(item_id)}",
        kind="paper",
        title=title,
        aliases=[alias for alias in [str(item.get("DOI", "")), str(item.get("URL", ""))] if alias],
        tags=tags,
        source={"type": "csl-json", "path": str(path)},
        metadata={
            "year": year,
            "authors": authors,
            "doi": item.get("DOI", ""),
            "url": item.get("URL", ""),
            "venue": item.get("container-title", ""),
        },
        summary=str(item.get("abstract", ""))[:600],
    )


def ingest_bibtex(store: GraphStore, path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    count = 0
    for entry_type, key, fields in parse_bibtex(text):
        title = fields.get("title", key)
        authors = [part.strip() for part in fields.get("author", "").replace("\n", " ").split(" and ") if part.strip()]
        node = Node(
            id=f"paper:{slugify(key)}",
            kind="paper",
            title=strip_braces(title),
            aliases=[fields.get("doi", ""), fields.get("url", "")],
            tags=[entry_type],
            source={"type": "bibtex", "path": str(path)},
            metadata={
                "year": fields.get("year", ""),
                "authors": authors,
                "doi": fields.get("doi", ""),
                "url": fields.get("url", ""),
                "venue": fields.get("journal", "") or fields.get("booktitle", ""),
            },
            summary=strip_braces(fields.get("abstract", ""))[:600],
        )
        store.add_node(node)
        count += 1
    return count


def parse_bibtex(text: str) -> list[tuple[str, str, dict[str, str]]]:
    entries: list[tuple[str, str, dict[str, str]]] = []
    for match in re.finditer(r"@(\w+)\s*\{\s*([^,]+),", text):
        entry_type = match.group(1).lower()
        key = match.group(2).strip()
        start = match.end()
        end = find_matching_brace(text, match.start())
        if end == -1:
            continue
        body = text[start:end]
        fields: dict[str, str] = {}
        for field_match in re.finditer(r"(\w+)\s*=\s*(\{(?:[^{}]|\{[^{}]*\})*\}|\"[^\"]*\"|[^,\n]+)\s*,?", body, re.S):
            name = field_match.group(1).lower()
            value = field_match.group(2).strip().strip(",").strip()
            fields[name] = strip_braces(value)
        entries.append((entry_type, key, fields))
    return entries


def find_matching_brace(text: str, at_pos: int) -> int:
    start = text.find("{", at_pos)
    if start == -1:
        return -1
    depth = 0
    for index in range(start, len(text)):
        char = text[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index
    return -1


def strip_braces(value: str) -> str:
    value = value.strip()
    if (value.startswith("{") and value.endswith("}")) or (value.startswith('"') and value.endswith('"')):
        value = value[1:-1]
    return re.sub(r"\s+", " ", value).strip()


def extract_csl_year(item: dict[str, Any]) -> str:
    issued = item.get("issued")
    if isinstance(issued, dict):
        date_parts = issued.get("date-parts")
        if isinstance(date_parts, list) and date_parts and date_parts[0]:
            return str(date_parts[0][0])
    return ""


def format_csl_name(author: dict[str, Any]) -> str:
    literal = author.get("literal")
    if literal:
        return str(literal)
    given = str(author.get("given", "")).strip()
    family = str(author.get("family", "")).strip()
    return " ".join(part for part in [given, family] if part)

