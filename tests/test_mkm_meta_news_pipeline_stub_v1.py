"""Shape check for RQ-011 meta-news stub fixture ([HYPO], research_only)."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "docs/final/artifacts/fixtures/mkm_meta_news_pipeline_stub_v1.example.json"


def test_mkm_meta_news_pipeline_stub_example_json_shape() -> None:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert data.get("schema") == "mkm_meta_news_pipeline_stub_v1"
    for key in ("field", "lenses", "conflict", "final", "audit", "boundary_ack", "hypothesis_tier"):
        assert key in data, f"missing top-level key: {key}"
    logos = data["lenses"]["logos"]
    assert logos.get("role") == "NON_GATING"
    assert "weights" in data["audit"]
