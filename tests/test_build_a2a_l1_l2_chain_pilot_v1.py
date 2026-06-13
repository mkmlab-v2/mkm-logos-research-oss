"""L1→L2 chain pilot smoke."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.build_a2a_l1_l2_chain_pilot_v1 import LANE_OPS_PACKS, ROOT, build_chain_document

DEFAULT_INDEX = ROOT / "storage/meta/mkm_ops_memory_index_v1.json"


def test_build_chain_document_infra_ms_ok():
    if not DEFAULT_INDEX.is_file():
        return  # env without ops index
    doc = build_chain_document(ROOT, lanes=["infra", "ms"])
    assert doc["schema"] == "a2a_l1_l2_chain_pilot_v1"
    assert doc["chain_ok"] is True
    assert len(doc["lanes"]) == 2
    infra = doc["lanes"][0]
    assert infra["l1_skim_inject"]["inject_tokens"] >= 32
    assert infra["l2_a2a_compress"]["decision"] == "compressed"
    assert infra["chain_kpi"]["l1_savings_ratio_vs_naive"] > 0.99


def test_build_chain_all_lanes_ok():
    if not DEFAULT_INDEX.is_file():
        return
    doc = build_chain_document(ROOT, lanes=sorted(LANE_OPS_PACKS.keys()))
    assert doc["chain_ok"] is True
    assert doc["aggregate"]["lane_count"] == len(LANE_OPS_PACKS)


def test_emit_script_writes_json(tmp_path, monkeypatch):
    if not DEFAULT_INDEX.is_file():
        return
    out = tmp_path / "chain.json"
    monkeypatch.setattr(
        "sys.argv",
        ["build_a2a_l1_l2_chain_pilot_v1.py", "--lane", "infra", "--out", str(out)],
    )
    from scripts.build_a2a_l1_l2_chain_pilot_v1 import main

    assert main() == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload.get("chain_ok") is True
