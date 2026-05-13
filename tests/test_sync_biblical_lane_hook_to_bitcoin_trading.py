from __future__ import annotations

import json
from pathlib import Path

import pytest

# Workspace-root test: sync script builds BTC hook JSON.


def test_merge_general_prophecy_explainable_hook(tmp_path: Path) -> None:
    from scripts.sync_biblical_lane_hook_to_bitcoin_trading import (
        build_hook,
        merge_general_prophecy_explainable_hook,
    )

    exp = tmp_path / "general_prophecy_explainable_latest.json"
    exp.write_text('{"schema": "x", "questions": []}', encoding="utf-8")
    prophecy = {"prophecy": {"base_scenario": {"direction_bias": "neutral"}}, "operator_brief": {}}
    status = {"live_trading": {"allowed": True, "phase": "x", "lane": "biblical_only"}}
    h = build_hook(prophecy, status, "BTCUSDT")
    merge_general_prophecy_explainable_hook(h, exp)
    ge = h["reference_only_extensions"]["general_prophecy_explainable"]
    assert ge["enabled"] is True
    assert ge["reference_only"] is True
    assert ge["must_not_trigger_orders"] is True
    assert "source_artifact" in ge
    assert h["source_artifacts"].get("general_prophecy_explainable") == ge["source_artifact"]


def test_build_hook_schema_and_paths():
    from scripts.sync_biblical_lane_hook_to_bitcoin_trading import build_hook

    prophecy = {
        "prophecy": {
            "base_scenario": {
                "direction_bias": "bull",
                "confidence": 0.55,
                "regime_label": "mixed-recent",
            }
        },
        "operator_brief": {"today_action": "hold"},
    }
    status = {
        "live_trading": {
            "lane": "biblical_only",
            "phase": "precommercial",
            "allowed": False,
            "reasons_if_blocked": ["x"],
            "policy": "p",
        }
    }
    h = build_hook(prophecy, status, "BTCUSDT")
    assert h["schema_version"] == "biblical_single_lane_trading_hook_v1"
    assert h["instrument"] == "BTCUSDT"
    assert h["market"] == "BTC"
    assert h["live_trading"]["allowed"] is False
    assert h["prophecy_snapshot"]["direction_bias"] == "bull"


@pytest.mark.skipif(
    not Path("docs/final/artifacts/kospi_biblical_prophecy_output_v2_latest.json").is_file()
    or not Path("docs/final/artifacts/kospi_biblical_single_lane_stability_status_latest.json").is_file(),
    reason="artifact JSON not present",
)
def test_sync_script_smoke(tmp_path: Path) -> None:
    import subprocess
    import sys

    out = tmp_path / "hook.json"
    r = subprocess.run(
        [sys.executable, "scripts/sync_biblical_lane_hook_to_bitcoin_trading.py", "--out", str(out)],
        cwd=Path.cwd(),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stderr
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data.get("schema_version") == "biblical_single_lane_trading_hook_v1"
    ex = Path("docs/final/artifacts/general_prophecy_explainable_latest.json")
    if ex.is_file():
        ref = data.get("reference_only_extensions") or {}
        assert "general_prophecy_explainable" in ref
        assert ref["general_prophecy_explainable"].get("must_not_trigger_orders") is True
