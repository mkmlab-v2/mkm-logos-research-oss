"""R3 GO aligned artifact pointer (offline)."""

from __future__ import annotations

import json
from pathlib import Path


def test_build_ops_r3_go_aligned_pointer_v1_smoke(tmp_path: Path) -> None:
    from scripts.build_ops_r3_go_aligned_pointer_v1 import build_pointer

    parallel = tmp_path / "reports" / "parallel_ops_round_mission_log_r3_latest.json"
    parallel.parent.mkdir(parents=True)
    parallel.write_text(
        json.dumps(
            {
                "schema": "parallel_ops_mission_log_r3_v1",
                "lanes": {
                    "live_patrol": {"ok": True, "go": "GO"},
                    "vps_go_scp": {"ok": True, "aligned": True},
                },
            }
        ),
        encoding="utf-8",
    )

    from scripts import build_ops_r3_go_aligned_pointer_v1 as mod

    orig = mod.ROOT
    mod.ROOT = tmp_path  # type: ignore[misc]
    try:
        doc = build_pointer()
    finally:
        mod.ROOT = orig  # type: ignore[misc]

    assert doc["schema"] == "ops_r3_go_aligned_pointer_v1"
    assert doc["go_aligned_summary"]["parallel_ops_ok"] is True
    assert doc["track_wall"]["prophecy_auto_promote"] is False


def test_run_logos_track_l_l1_readiness_v1_dry(monkeypatch) -> None:
    from scripts import run_logos_track_l_l1_readiness_v1 as mod

    def fake_run(script, *extra):
        if script.name.startswith("run_logos_track_l_l0"):
            return 0, {"l0_ok": True}
        return 0, {"overall_ok": True}

    monkeypatch.setattr(mod, "_run_py", fake_run)
    doc = mod.build_report(skip_policy=False)
    assert doc["l1_ok"] is True
