"""PersonaDiary Logos sidebar smoke v1."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_PROPHECY_KEYS = {
    "directional_hit_rate",
    "directional_hit_rate_active",
    "sharpe",
    "total_return",
    "alignment_pass_rate",
}


@pytest.mark.skipif(
    __import__("importlib").util.find_spec("jsonschema") is None,
    reason="jsonschema not installed",
)
def test_personadiary_logos_sidebar_smoke_schema_and_walls() -> None:
    import jsonschema

    out = ROOT / "docs/final/artifacts/personadiary_logos_sidebar_smoke_v1_latest.json"
    if not out.is_file():
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts/build_personadiary_logos_sidebar_smoke_v1.py")],
            cwd=str(ROOT),
            timeout=60,
        )
        assert proc.returncode == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    schema = json.loads(
        (
            ROOT / "docs/final/schemas/personadiary_logos_sidebar_smoke_v1.schema.json"
        ).read_text(encoding="utf-8")
    )
    jsonschema.validate(instance=doc, schema=schema)
    assert doc.get("prophecy_vote") == "none"
    assert doc.get("track_a_blocked") is True
    assert doc.get("send_gate") == "HOLD"
    assert doc.get("sidebar_generation_ok") is True
    assert len(doc.get("hits") or []) == 3
    assert doc.get("forbidden_violations") == []
    assert doc.get("ok") is True
    pools = doc.get("candidate_pools") or {}
    assert len(pools.get("logos_ann_lite") or []) > 0
    assert len(pools.get("graphrag_motif") or []) > 0
    assert len(pools.get("concept_bridge") or []) > 0
    assert (doc.get("rerank_contract") or {}).get("client_local_diary") is True
    blob = json.dumps(doc)
    for key in FORBIDDEN_PROPHECY_KEYS:
        assert f'"{key}"' not in blob
    for hit in doc.get("hits") or []:
        assert hit.get("hit_type") in {
            "logos_ann_lite",
            "graphrag_motif",
            "concept_bridge",
        }
        assert hit.get("verse_id") or hit.get("node_id") or hit.get("concept_id")
