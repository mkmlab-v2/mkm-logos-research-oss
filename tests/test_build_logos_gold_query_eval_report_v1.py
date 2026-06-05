#!/usr/bin/env python3
"""Tests for logos gold query eval (CPU, artifact-only)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GOLD = ROOT / "docs/final/fixtures/logos_gold_query_eval_v1.json"
BUILDER = ROOT / "scripts/build_logos_gold_query_eval_report_v1.py"


def test_normalize_verse_in_builder_module() -> None:
    sys.path.insert(0, str(ROOT / "scripts"))
    import build_logos_gold_query_eval_report_v1 as mod

    assert mod.normalize_verse_ref("greek::John.19.34") == "John.19.34"
    assert mod.normalize_verse_ref("node_verse_john_19_34") == "John.19.34"
    assert mod.normalize_verse_ref("Isa.28.8") == "Isa.28.8"


def test_gold_eval_report_builds() -> None:
    out = ROOT / "reports/test_logos_gold_query_eval_v1_latest.json"
    proc = subprocess.run(
        [sys.executable, str(BUILDER), "--out-json", str(out)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    body = json.loads(out.read_text(encoding="utf-8"))
    assert body["schema"] == "logos_gold_query_eval_report_v1"
    assert body["gpu_used"] is False
    assert body["nemotron_paths_touched"] is False
    q06 = next(r for r in body["rows"] if r["id"] == "q06")
    assert q06["router"]["path_gold_hits"] >= 1
    assert "John.19.34" in q06["router"]["gold_hits"] or any(
        h.startswith("John.19") for h in q06["router"]["gold_hits"]
    )


def test_gold_fixture_schema() -> None:
    doc = json.loads(GOLD.read_text(encoding="utf-8"))
    assert doc["schema"] == "logos_gold_query_eval_v1"
    ids = {it["id"] for it in doc["items"]}
    assert "q06" in ids
    assert "q04" in ids


def test_rag_snippet_verse_extraction() -> None:
    sys.path.insert(0, str(ROOT / "scripts"))
    import build_logos_gold_query_eval_report_v1 as mod

    insight = {
        "rag_evidence": [
            {
                "source_id": "logos_subgraph:path_new_covenant:docs/final/artifacts/x.json",
                "snippet": 'steps=["concept:x", "verse:Jer.31.33"]',
            }
        ]
    }
    verses = mod._collect_rag_verses(insight)
    assert "Jer.31.33" in verses


def test_rag_verse_id_field_extraction() -> None:
    sys.path.insert(0, str(ROOT / "scripts"))
    import build_logos_gold_query_eval_report_v1 as mod

    insight = {
        "rag_evidence": [
            {"verse_id": "Neh.4.9", "source": "election_graphrag_router"},
            {"verse_id": "1Chr.12.32", "source": "election_graphrag_router"},
        ]
    }
    verses = mod._collect_rag_verses(insight)
    assert "Neh.4.9" in verses
    assert "1Chr.12.32" in verses
