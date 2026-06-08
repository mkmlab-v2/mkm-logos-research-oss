"""tp02 lexicon_dense A2A bench smoke."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.build_a2a_tp02_lexicon_dense_bench_v1 import build_bench_document

ROOT = Path(__file__).resolve().parents[1]


def test_build_bench_document_schema_and_ok():
    doc = build_bench_document(turns=2)
    assert doc["schema"] == "a2a_tp02_lexicon_dense_bench_v1"
    assert doc["target_point_id"] == "tp02_btrack_prophecy_executor_wire"
    assert doc["bench_config"]["scenario"] == "lexicon_dense"
    assert doc["bench_ok"] is True
    headline = doc["kpi_headline"]
    mock_avg = headline.get("mock_avg_savings_ratio")
    assert mock_avg is not None
    assert mock_avg >= 0.35, f"lexicon_dense fixture too short for ROI bench: {mock_avg}"
    assert headline.get("wire_avg_envelope_vs_packet_savings") is not None
    token_ins = doc["trust_packet_mock"]["metrics"].get("token_in_by_turn") or []
    assert token_ins and min(token_ins) >= 32, "turns should exceed compress skip threshold"


def test_emit_script_writes_json(tmp_path, monkeypatch):
    out = tmp_path / "bench.json"
    monkeypatch.setattr(
        "sys.argv",
        ["build_a2a_tp02_lexicon_dense_bench_v1.py", "--turns", "2", "--out", str(out)],
    )
    from scripts.build_a2a_tp02_lexicon_dense_bench_v1 import main

    assert main() == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload.get("schema") == "a2a_tp02_lexicon_dense_bench_v1"
    assert payload.get("bench_ok") is True
