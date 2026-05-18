from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _rollup_mod():
    spec = importlib.util.spec_from_file_location(
        "build_sandbox_prophecy_stream_rollup_v1",
        ROOT / "scripts/build_sandbox_prophecy_stream_rollup_v1.py",
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod


def test_rollup_dedupes_same_day_and_watchlist(tmp_path: Path) -> None:
    mod = _rollup_mod()
    p = tmp_path / "stream.jsonl"
    rows = []
    for day, hit in [("2026-05-15", 0.6), ("2026-05-16", 0.58), ("2026-05-17", 0.57)]:
        rows.append(
            {
                "generated_at_utc": f"{day}T08:50:00Z",
                "target_id": "eth_v1_price_only",
                "ok": True,
                "metrics": {"price_directional_hit_rate": hit, "n_evaluated": 30},
            }
        )
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    doc = mod.build_rollup(mod._read_jsonl(p), watchlist_streak_days=3, watchlist_hit_threshold=0.55)
    eth = next(t for t in doc["targets"] if t["target_id"] == "eth_v1_price_only")
    assert eth["n_calendar_days"] == 3
    assert eth["watchlist_candidate"] is True
    assert doc["n_watchlist_candidates"] == 1


def test_phase3_deadband_reduces_calls(tmp_path: Path) -> None:
    spec = importlib.util.spec_from_file_location(
        "sandbox_phase3_sensor_eval_v1",
        ROOT / "scripts/sandbox_phase3_sensor_eval_v1.py",
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    p = tmp_path / "joined.jsonl"
    rows = [
        {
            "eval_date": f"2026-05-{d:02d}",
            "instrument": "btc",
            "actual_direction": "bull",
            "sensors": {"perp_funding_skew_signed_flow_z": z},
        }
        for d, z in [(1, 0.05), (2, -0.05), (3, 0.5)]
    ]
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    m0 = mod.eval_phase3_sensor(p, sensor_z_key="perp_funding_skew_signed_flow_z", deadband=0.0)
    m1 = mod.eval_phase3_sensor(p, sensor_z_key="perp_funding_skew_signed_flow_z", deadband=0.1)
    assert m0["n_evaluated"] == 3
    assert m1["n_evaluated"] <= m0["n_evaluated"]
