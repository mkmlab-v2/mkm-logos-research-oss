"""Tier 2 L2 shadow measurement smoke."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.build_a2a_l2_shadow_measurement_v1 import build_shadow_document


def test_shadow_document_schema_and_ok():
    doc = build_shadow_document(Path(__file__).resolve().parents[1], lane="infra")
    assert doc["schema"] == "a2a_l2_shadow_measurement_v1"
    assert doc["tier"] == "tier2_shadow"
    assert doc["shadow_ok"] is True
    headline = doc["kpi_headline"]
    assert headline.get("inject_tokens", 0) >= 32
    assert headline.get("decision") == "compressed"
    assert headline.get("l2_savings_ratio") is not None


def test_emit_script_writes_json_and_log(tmp_path, monkeypatch):
    out = tmp_path / "shadow.json"
    log = tmp_path / "shadow.jsonl"
    monkeypatch.setattr(
        "sys.argv",
        [
            "build_a2a_l2_shadow_measurement_v1.py",
            "--lane",
            "ms",
            "--out",
            str(out),
            "--log",
            str(log),
            "--append-log",
        ],
    )
    from scripts.build_a2a_l2_shadow_measurement_v1 import main

    assert main() == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload.get("shadow_ok") is True
    lines = log.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row["schema"] == "a2a_l2_shadow_log_v1"
    assert row["inject_source"] == "lane:ms"
