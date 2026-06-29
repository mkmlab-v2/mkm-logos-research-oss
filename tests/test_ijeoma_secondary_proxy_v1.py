"""Smoke: IJEOMA_SECONDARY_PROXY_v1.json schema and Fact-Lock invariants."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROXY = ROOT / "docs/research/raw/IJEOMA_SECONDARY_PROXY_v1.json"
CANON = ROOT / "docs/sasang-origin/정교동의수세보원원문.txt"


def test_secondary_proxy_schema_and_gates() -> None:
    doc = json.loads(PROXY.read_text(encoding="utf-8"))
    assert doc["schema"] == "ijeoma_secondary_proxy_v1"
    assert doc["canon_status"] == "not_acquired"
    assert doc["primary_hanja_chunk_count"] == 0
    assert doc["send_gate"] == "HOLD"
    frags = doc["fragments"]
    assert len(frags) >= 15
    for f in frags:
        assert f["canon_claim"] is False
        assert "source_tier" in f and "layer" in f
    unverified = [f for f in frags if f.get("verification_status") == "UNVERIFIED"]
    assert unverified
    canon_frags = [f for f in frags if f["source_tier"] == "T0_workspace_canon"]
    assert len(canon_frags) >= 8
    for f in canon_frags:
        assert f["source_path"] == "docs/sasang-origin/정교동의수세보원원문.txt"
        start, end = f["line_range"]
        lines = CANON.read_text(encoding="utf-8").splitlines()
        excerpt = "\n".join(lines[start - 1 : end])
        key = f["quote_hanja"].split("…")[0].split("…")[0][:12]
        assert any(part in excerpt for part in key.split() if len(part) >= 2), (
            f"{f['id']}: quote not found at line_range"
        )
