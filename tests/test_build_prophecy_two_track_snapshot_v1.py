from __future__ import annotations

import json
from pathlib import Path

from scripts.build_prophecy_two_track_snapshot_v1 import build


def test_build_two_track_fusion_policy():
    template = {
        "schema": "prophecy_two_track_snapshot_v1",
        "fusion_policy": {},
        "track_a_trading_theory": {},
        "track_b_historical_omen": {},
    }
    prophecy = {
        "market": "KOSPI",
        "lane": "biblical_only",
        "gates": {
            "internal_gate": {"pass": True},
            "external_reality_gate": {"pass": True},
            "stability_gate": {"stability_go": False, "ready_streak": 1, "streak_required": 3},
        },
        "operator_brief": {"today_action": "hold", "escalation": "watch"},
        "live_trading": {"allowed": False, "phase": "precommercial"},
    }
    gate = {"stage": "precommercial_ready", "precommercial_ready": True}
    general = {
        "schema": "general_prophecy_registry_v1",
        "research_rail": "B",
        "questions": [{"resolution": {"status": "pending"}}, {"resolution": {"status": "resolved"}}],
    }
    snap = build(template, prophecy, gate, general, Path("docs/final/artifacts/general_prophecy_latest.json"), {})
    assert snap["fusion_policy"]["track_b_must_not_trigger_orders"] is True
    assert snap["track_a_trading_theory"]["summary"]["gates_pass_snapshot"]["stability_go"] is False
    assert snap["track_b_historical_omen"]["registry_summary"]["pending_resolution_count"] == 1


def test_smoke_latest_artifacts():
    out = Path("docs/final/artifacts/prophecy_two_track_snapshot_v1_latest.json")
    if not Path("docs/final/artifacts/prophecy_two_track_snapshot_v1_template.json").is_file():
        return
    import subprocess
    import sys

    r = subprocess.run(
        [sys.executable, "scripts/build_prophecy_two_track_snapshot_v1.py"],
        cwd=Path.cwd(),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stderr
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data.get("schema") == "prophecy_two_track_snapshot_v1"
