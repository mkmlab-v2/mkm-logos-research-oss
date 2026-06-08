"""tp03 Track C chain ref A2A pilot smoke."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.build_a2a_tp03_chain_ref_pilot_v1 import build_pilot_document

ROOT = Path(__file__).resolve().parents[1]


def test_build_pilot_document_schema():
    doc = build_pilot_document(ROOT)
    assert doc["schema"] == "a2a_tp03_chain_ref_pilot_v1"
    assert doc["target_point_id"] == "tp03_trackc_multilens_chain_refs"
    assert doc["status"] == "PILOT"
    assert int(doc.get("artifacts_present") or 0) >= 1
    agg = doc["aggregate_pointer_vs_full"]
    assert agg["full_body_tokens_sum"] >= agg["pointer_tokens_sum"]
    assert agg["reduction_ratio"] is not None


def test_pointer_smaller_than_full_body():
    doc = build_pilot_document(ROOT)
    for row in doc.get("artifacts") or []:
        if not row.get("exists"):
            continue
        assert row["pointer_tokens"] < row["full_body_tokens"]


def test_emit_script_writes_json(tmp_path, monkeypatch):
    out = tmp_path / "pilot.json"
    monkeypatch.setattr(
        "sys.argv",
        ["build_a2a_tp03_chain_ref_pilot_v1.py", "--out", str(out)],
    )
    from scripts.build_a2a_tp03_chain_ref_pilot_v1 import main

    assert main() == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload.get("schema") == "a2a_tp03_chain_ref_pilot_v1"
