"""Hangul curated ACTIVE promotion packet gates (offline)."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_active_promotion_packet_schema_when_present() -> None:
    path = ROOT / "reports/hangul_curated_active_promotion_packet_v1_latest.json"
    if not path.is_file():
        return
    doc = json.loads(path.read_text(encoding="utf-8"))
    assert doc.get("schema") == "hangul_curated_active_promotion_packet_v1"
    assert "promotion_ready" in doc
    assert doc.get("promotion_scope", {}).get("ms_paste_headline_auto_update") is False
    gates = doc.get("promotion_gates") or {}
    assert "jaccard_drop_vs_frozen_active_pass" in gates
