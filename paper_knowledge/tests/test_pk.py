from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from pk.brief import ranked_nodes, write_planning_brief
from pk.importers import ingest_bibtex
from pk.markdown import ingest_markdown_file
from pk.model import Edge, Node
from pk.store import GraphStore
from pk.systematize import add_tag_relations
from pk.viewer import write_viewer_data


class PaperKnowledgeTests(unittest.TestCase):
    def test_markdown_ingest_adds_nodes_and_edges(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            note = Path(tmp) / "note.md"
            note.write_text(
                """---
id: paper:test2024
kind: paper
title: Test Paper
tags: robustness, testing
---

Links to [[method:test-method]].

uses_method:: method:test-method
supports:: claim:test-claim
""",
                encoding="utf-8",
            )
            store = GraphStore(Path(tmp) / "graph.json")
            ingest_markdown_file(store, note)
            self.assertIn("paper:test2024", store.nodes)
            self.assertIn("method:test-method", store.nodes)
            edge_types = {edge.type for edge in store.edges}
            self.assertIn("uses_method", edge_types)
            self.assertIn("supports", edge_types)

    def test_bibtex_ingest_adds_paper(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "refs.bib"
            path.write_text(
                """@article{smith2024,
  title={A Robust Method},
  author={Smith, Ada and Yamada, Taro},
  year={2024},
  doi={10.0000/test}
}
""",
                encoding="utf-8",
            )
            store = GraphStore(Path(tmp) / "graph.json")
            count = ingest_bibtex(store, path)
            self.assertEqual(count, 1)
            self.assertEqual(store.nodes["paper:smith2024"].title, "A Robust Method")

    def test_related_by_tag_and_brief(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = GraphStore(Path(tmp) / "graph.json")
            store.add_node(Node(id="paper:a", kind="paper", title="Alpha Robustness", tags=["robustness"]))
            store.add_node(Node(id="paper:b", kind="paper", title="Beta", tags=["robustness"]))
            added = add_tag_relations(store)
            self.assertEqual(added, 1)
            matches = ranked_nodes(store, "robustness", limit=5)
            self.assertEqual(matches[0][1].id, "paper:a")
            out = Path(tmp) / "brief.md"
            write_planning_brief(store, "robustness", out)
            self.assertIn("Paper Knowledge Planning Brief", out.read_text(encoding="utf-8"))

    def test_store_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "graph.json"
            store = GraphStore(path)
            store.add_node(Node(id="paper:a", kind="paper", title="A"))
            store.add_node(Node(id="claim:c", kind="claim", title="C"))
            store.add_edge(Edge(source="paper:a", target="claim:c", type="supports"))
            store.save()
            raw = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(raw["nodes"]["paper:a"]["title"], "A")
            loaded = GraphStore.load(path)
            self.assertEqual(len(loaded.edges), 1)


    def test_viewer_data_writes_browser_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = GraphStore(Path(tmp) / "graph.json")
            store.add_node(Node(id="paper:a", kind="paper", title="A"))
            out = Path(tmp) / "graph-data.js"
            write_viewer_data(store, out)
            text = out.read_text(encoding="utf-8")
            self.assertTrue(text.startswith("window.PAPER_KNOWLEDGE_GRAPH = "))
            self.assertIn("\"nodes\": 1", text)

    def test_viewer_canvas_uses_stable_responsive_contract(self) -> None:
        viewer_root = Path(__file__).resolve().parents[1] / "viewer"
        css = (viewer_root / "viewer.css").read_text(encoding="utf-8")
        script = (viewer_root / "viewer.js").read_text(encoding="utf-8")

        self.assertIn("height: 100dvh;", css)
        self.assertIn("grid-template-rows: auto minmax(0, 1fr);", css)
        self.assertIn("position: absolute;", css)
        self.assertIn("height: clamp(360px, 65dvh, 560px);", css)
        self.assertNotIn("min-height: calc(100vh - 73px);", css)
        self.assertIn("new ResizeObserver", script)
        self.assertIn("graphPanel.clientWidth", script)
        self.assertNotIn('window.addEventListener("resize", () =>', script)


if __name__ == "__main__":
    unittest.main()

