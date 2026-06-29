from __future__ import annotations

import json
from pathlib import Path

from scripts.logos_deep_research_graph_evidence_v1 import (
    build_graph_paths,
    quote_hash,
    verse_id_from_node,
)

_ROOT = Path(__file__).resolve().parents[1]


def test_verse_id_from_node() -> None:
    assert verse_id_from_node("aramaic::Dan.2.10") == "Dan.2.10"
    assert verse_id_from_node("bad") is None


def test_quote_hash_stable() -> None:
    h1 = quote_hash("abc")
    h2 = quote_hash("abc")
    assert h1 == h2
    assert h1.startswith("sha256:")


def test_build_graph_paths_minimal() -> None:
    edges = [
        {
            "src_node_id": "aramaic::Dan.2.10",
            "dst_node_id": "aramaic::Dan.2.11",
            "edge_type": "timeline_anchor",
            "weight": 0.9,
            "evidence": "test",
        }
    ]
    paths = build_graph_paths(edges)
    assert len(paths) == 1
    assert paths[0]["verse_ids"] == ["Dan.2.10", "Dan.2.11"]


def test_enrich_graph_distill_validates(tmp_path: Path) -> None:
    jsonschema = __import__("jsonschema")
    schema_path = _ROOT / "docs/final/schemas/logos_deep_research_distill_v1.schema.json"
    bundle = _ROOT / "tests/fixtures/logos_corpus_graph_bundle_minimal_distill_v1.json"
    edges = tmp_path / "edges.jsonl"
    edges.write_text(
        json.dumps(
            {
                "src_node_id": "aramaic::Gen.1.1",
                "dst_node_id": "aramaic::Gen.1.2",
                "edge_type": "timeline_anchor",
                "weight": 0.95,
                "evidence": "x",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    out = tmp_path / "distill.json"
    import subprocess
    import sys

    cp = subprocess.run(
        [
            sys.executable,
            str(_ROOT / "scripts/run_lens_logos_deep_fusion.py"),
            "--bundle-json",
            str(bundle),
            "--enrich-graph",
            "--write-template",
            str(out),
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        check=False,
        env={
            **__import__("os").environ,
            "PYTHONPATH": str(_ROOT),
        },
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(schema).validate(doc)
    assert doc.get("version") == "1.0.2"
    assert len(doc.get("graph_paths") or []) >= 1
