from __future__ import annotations

import json
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]


def test_smoke_artifact_schema() -> None:
    path = _ROOT / "docs/final/artifacts/compression_open_bench_logos_audit_smoke_v1_latest.json"
    if not path.is_file():
        pytest.skip("smoke artifact not built")
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    assert doc.get("schema") == "compression_open_bench_logos_audit_smoke_v1"
    assert doc.get("track_wall", {}).get("ms_headline_merge_forbidden") is True


def test_one_pager_b2b_exists() -> None:
    path = _ROOT / "docs/final/artifacts/logos_rag_integrity_audit_one_pager_b2b_v1_latest.md"
    if not path.is_file():
        pytest.skip("one pager not rendered")
    text = path.read_text(encoding="utf-8")
    assert "SEND_GATE: HOLD" in text
    assert "citation_valid" in text.lower() or "citation_valid themes" in text
