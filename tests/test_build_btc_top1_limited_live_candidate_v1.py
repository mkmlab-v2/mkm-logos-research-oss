from __future__ import annotations

import json
from pathlib import Path

from scripts import build_btc_top1_limited_live_candidate_v1 as mod


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_build_top1_limited_live_candidate_ready(tmp_path: Path, monkeypatch) -> None:
    sweep = tmp_path / "sweep.json"
    gates = tmp_path / "gates.json"
    guard = tmp_path / "guard.json"
    out = tmp_path / "out.json"

    _write(
        sweep,
        {
            "best_candidate": {
                "params": {"w_cross": 1.5},
                "metrics": {"price_directional_hit_rate": 0.65, "n_evaluated": 60},
                "delta_vs_baseline": 0.12,
            }
        },
    )
    _write(gates, {"all_gates_passed": True, "strict_passed": True})
    _write(guard, {"enforcement_enabled": True, "should_rollback": False})

    monkeypatch.setattr(
        "sys.argv",
        [
            "build_btc_top1_limited_live_candidate_v1.py",
            "--sweep-json",
            str(sweep),
            "--promotion-gates-json",
            str(gates),
            "--causal-guard-json",
            str(guard),
            "--base-position-usd",
            "100",
            "--limited-live-ratio",
            "0.1",
            "--out",
            str(out),
        ],
    )
    assert mod.main() == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["decision"]["status"] == "READY_LIMITED_LIVE"
    assert doc["limited_live_policy"]["limited_position_usd"] == 10.0
