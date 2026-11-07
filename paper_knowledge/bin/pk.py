#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pk.brief import write_planning_brief
from pk.importers import ingest_bibtex, ingest_csl_json
from pk.markdown import ingest_markdown_path, slugify
from pk.model import Edge, Node
from pk.store import DEFAULT_STORE, GraphStore
from pk.systematize import systematize
from pk.viewer import DEFAULT_VIEWER_DATA, write_viewer_data


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        args.func(args)
    except (OSError, ValueError, RuntimeError, TypeError, KeyError, json.JSONDecodeError) as exc:
        emit(f"ERROR {exc}")
        return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage the independent paper knowledge graph.")
    parser.set_defaults(func=cmd_help)
    subparsers = parser.add_subparsers(dest="command")

    init_parser = subparsers.add_parser("init", help="Create or refresh an empty graph store.")
    add_common_store(init_parser)
    init_parser.set_defaults(func=cmd_init)

    add_paper = subparsers.add_parser("add-paper", help="Add one paper node.")
    add_common_store(add_paper)
    add_paper.add_argument("--id", required=True, help="Paper id or citekey; namespace optional.")
    add_paper.add_argument("--title", required=True)
    add_paper.add_argument("--year", default="")
    add_paper.add_argument("--authors", default="", help="Semicolon-separated authors.")
    add_paper.add_argument("--tags", default="", help="Comma-separated tags.")
    add_paper.add_argument("--doi", default="")
    add_paper.add_argument("--url", default="")
    add_paper.set_defaults(func=cmd_add_paper)

    add_edge = subparsers.add_parser("add-edge", help="Add one typed graph edge.")
    add_common_store(add_edge)
    add_edge.add_argument("--source", required=True)
    add_edge.add_argument("--target", required=True)
    add_edge.add_argument("--type", required=True)
    add_edge.add_argument("--evidence", default="")
    add_edge.add_argument("--confidence", type=float, default=0.5)
    add_edge.set_defaults(func=cmd_add_edge)

    ingest_md = subparsers.add_parser("ingest-markdown", help="Ingest scoped Markdown notes.")
    add_common_store(ingest_md)
    ingest_md.add_argument("path", type=Path)
    ingest_md.add_argument("--allow-outside", action="store_true")
    ingest_md.set_defaults(func=cmd_ingest_markdown)

    ingest_csl = subparsers.add_parser("ingest-csl", help="Ingest CSL JSON metadata.")
    add_common_store(ingest_csl)
    ingest_csl.add_argument("path", type=Path)
    ingest_csl.set_defaults(func=cmd_ingest_csl)

    ingest_bib = subparsers.add_parser("ingest-bibtex", help="Ingest BibTeX metadata.")
    add_common_store(ingest_bib)
    ingest_bib.add_argument("path", type=Path)
    ingest_bib.set_defaults(func=cmd_ingest_bibtex)

    syst = subparsers.add_parser("systematize", help="Refresh notes and deterministic relation hints.")
    add_common_store(syst)
    syst.add_argument("--notes", type=Path, default=ROOT / "notes")
    syst.add_argument("--out", type=Path, default=ROOT / "out" / "systematization_report.md")
    syst.add_argument("--allow-outside", action="store_true")
    syst.set_defaults(func=cmd_systematize)

    brief = subparsers.add_parser("brief", help="Write a planning brief for a query.")
    add_common_store(brief)
    brief.add_argument("--query", required=True)
    brief.add_argument("--out", type=Path, default=ROOT / "out" / "planning_brief.md")
    brief.add_argument("--limit", type=int, default=12)
    brief.set_defaults(func=cmd_brief)

    validate = subparsers.add_parser("validate", help="Validate graph consistency.")
    add_common_store(validate)
    validate.set_defaults(func=cmd_validate)

    viewer_data = subparsers.add_parser("viewer-data", help="Write browser-ready viewer graph data.")
    add_common_store(viewer_data)
    viewer_data.add_argument("--out", type=Path, default=DEFAULT_VIEWER_DATA)
    viewer_data.set_defaults(func=cmd_viewer_data)

    return parser


def add_common_store(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--store", type=Path, default=DEFAULT_STORE)


def cmd_help(args: argparse.Namespace) -> None:
    raise ValueError("choose a command")


def cmd_init(args: argparse.Namespace) -> None:
    store = GraphStore(args.store)
    store.save()
    emit(f"OK initialized {args.store}")


def cmd_add_paper(args: argparse.Namespace) -> None:
    store = GraphStore.load(args.store)
    paper_id = args.id if args.id.startswith("paper:") else f"paper:{slugify(args.id)}"
    node = Node(
        id=paper_id,
        kind="paper",
        title=args.title,
        tags=split_csv(args.tags),
        metadata={
            "year": args.year,
            "authors": [item.strip() for item in args.authors.split(";") if item.strip()],
            "doi": args.doi,
            "url": args.url,
        },
        aliases=[item for item in [args.doi, args.url] if item],
    )
    store.add_node(node)
    store.save()
    emit(f"OK added {paper_id}")


def cmd_add_edge(args: argparse.Namespace) -> None:
    store = GraphStore.load(args.store)
    store.add_edge(
        Edge(
            source=args.source,
            target=args.target,
            type=args.type,
            evidence=args.evidence,
            confidence=args.confidence,
        )
    )
    store.save()
    emit(f"OK added-edge {args.source} {args.type} {args.target}")


def cmd_ingest_markdown(args: argparse.Namespace) -> None:
    store = GraphStore.load(args.store)
    count = ingest_markdown_path(store, args.path, root=ROOT, allow_outside=args.allow_outside)
    errors = store.validate()
    if errors:
        raise ValueError("; ".join(errors[:5]))
    store.save()
    emit(f"OK ingested-markdown files={count}")


def cmd_ingest_csl(args: argparse.Namespace) -> None:
    store = GraphStore.load(args.store)
    count = ingest_csl_json(store, args.path)
    errors = store.validate()
    if errors:
        raise ValueError("; ".join(errors[:5]))
    store.save()
    emit(f"OK ingested-csl items={count}")


def cmd_ingest_bibtex(args: argparse.Namespace) -> None:
    store = GraphStore.load(args.store)
    count = ingest_bibtex(store, args.path)
    errors = store.validate()
    if errors:
        raise ValueError("; ".join(errors[:5]))
    store.save()
    emit(f"OK ingested-bibtex items={count}")


def cmd_systematize(args: argparse.Namespace) -> None:
    store = GraphStore.load(args.store)
    count = systematize(store, args.notes, root=ROOT, out_path=args.out, allow_outside=args.allow_outside)
    emit(f"OK systematized notes={count} report={args.out}")


def cmd_brief(args: argparse.Namespace) -> None:
    store = GraphStore.load(args.store)
    write_planning_brief(store, args.query, args.out, args.limit)
    emit(f"OK wrote-brief {args.out}")


def cmd_validate(args: argparse.Namespace) -> None:
    store = GraphStore.load(args.store)
    errors = store.validate()
    if errors:
        raise ValueError("; ".join(errors[:5]))
    emit(f"OK valid nodes={len(store.nodes)} edges={len(store.edges)}")


def cmd_viewer_data(args: argparse.Namespace) -> None:
    store = GraphStore.load(args.store)
    errors = store.validate()
    if errors:
        raise ValueError("; ".join(errors[:5]))
    write_viewer_data(store, args.out)
    emit(f"OK wrote-viewer-data {args.out}")


def split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def emit(message: str) -> None:
    sys.stdout.write(message + "\n")


if __name__ == "__main__":
    raise SystemExit(main())

