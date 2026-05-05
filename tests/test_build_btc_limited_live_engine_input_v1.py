from __future__ import annotations

import json
from pathlib import Path

from scripts import build_btc_limited_live_engine_input_v1 as mod


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_engine_input_ready_when_candidate_and_signoff_ok(tmp_path: Path, monkeypatch) -> None:
    candidate = tmp_path / "candidate.json"
    signoff = tmp_path / "signoff.json"
    out = tmp_path / "engine_input.json"

    _write(
        candidate,
        {
            "decision": {"tradable_candidate": True},
            "limited_live_policy": {
                "limited_position_usd": 10.0,
                "max_consecutive_losses": 3,
                "max_drawdown_pct": 2.0,
            },
            "candidate": {"params": {"w_cross": 1.5}, "metrics": {"price_directional_hit_rate": 0.65}},
        },
    )
    _write(signoff, {"decision": {"status": "APPROVE", "mode": "limited_live_deployment"}})

    monkeypatch.setattr(
        "sys.argv",
        [
            "build_btc_limited_live_engine_input_v1.py",
            "--candidate-json",
            str(candidate),
            "--signoff-json",
            str(signoff),
            "--approve-submit",
            "--out",
            str(out),
        ],
    )
    assert mod.main() == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["status"] == "READY_FOR_ENGINE_SUBMIT"
    assert doc["action"] == "submit_to_engine_queue"
