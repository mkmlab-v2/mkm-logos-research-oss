"""Tests for LTM index filter ([HYPO] / B-track)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from check_ltm_index_filter_v1 import check_concept_paths, load_filter  # noqa: E402
from mkm_ops_memory_index_lib_v1 import (  # noqa: E402
    LANE_OPS_PACKS,
    ensure_lane_pack_index,
    merge_overlay_nodes,
)


def test_load_filter_schema() -> None:
    doc = load_filter(ROOT / "docs/final/artifacts/ltm_index_filter_v1.json")
    assert doc["schema"] == "ltm_index_filter_v1"
    assert doc.get("hard_exclude_globs")


def test_check_concept_paths_no_hard_errors() -> None:
    doc = load_filter(ROOT / "docs/final/artifacts/ltm_index_filter_v1.json")
    errors, _warnings = check_concept_paths(ROOT, filter_doc=doc)
    assert errors == []


def test_hard_exclude_rejects_git_path() -> None:
    doc = load_filter(ROOT / "docs/final/artifacts/ltm_index_filter_v1.json")
    errors, _warnings = check_concept_paths(
        ROOT,
        filter_doc=doc,
        extra_paths=[".git/objects/abc"],
    )
    assert any("hard_exclude" in e for e in errors)


def test_ensure_lane_pack_web_ops_overlay_in_memory(tmp_path: Path) -> None:
    gate = tmp_path / "reports/web_ops_regime_gate_v1_latest.json"
    gate.parent.mkdir(parents=True, exist_ok=True)
    gate.write_text(
        json.dumps(
            {
                "gate_pass": True,
                "research_only": True,
                "track_wall": "B",
                "conflict_resolver": {"worst_final_action": "HOLD"},
                "cost_policy": {
                    "no_gpu_spinup": True,
                    "no_new_billing_charges": True,
                    "nebius_prepaid_only": True,
                },
                "operator_hint_ko": "test",
            }
        ),
        encoding="utf-8",
    )
    health = tmp_path / "reports/web_ops_regime_health_summary_v1_latest.json"
    health.write_text(
        json.dumps(
            {
                "health_ok": True,
                "gate_pass": True,
                "research_only": True,
                "worst_final_action": "HOLD",
                "balance": "ok",
                "observation_source": "test",
                "nebius_balance_usd": 25,
                "pointer_drift_detected": False,
            }
        ),
        encoding="utf-8",
    )
    index = {
        "nodes": {
            "prism_ops_mission_log_board": {"essence": "board"},
            "prism_ops_central_checkpoint": {"essence": "central"},
        }
    }
    merged = ensure_lane_pack_index(tmp_path, index, "web_ops")
    nodes = merged.get("nodes") or {}
    for node_id in LANE_OPS_PACKS["web_ops"]:
        assert node_id in nodes
