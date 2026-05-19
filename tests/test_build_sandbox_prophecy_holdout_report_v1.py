from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_holdout_pass_on_stable_high_hits(tmp_path: Path) -> None:
    spec = importlib.util.spec_from_file_location(
        "build_sandbox_prophecy_holdout_report_v1",
        ROOT / "scripts/build_sandbox_prophecy_holdout_report_v1.py",
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    rows = []
    for i, hit in enumerate([0.52, 0.54, 0.56, 0.58, 0.6, 0.62, 0.64, 0.66]):
        rows.append(
            {
                "generated_at_utc": f"2026-05-{10 + i:02d}T08:50:00Z",
                "target_id": "eth_v1_price_only",
                "ok": True,
                "metrics": {"price_directional_hit_rate": hit},
            }
        )
    doc = mod.build_holdout_report(rows, holdout_snapshot_days=3, train_min_snapshots=2)
    eth = next(t for t in doc["targets"] if t["target_id"] == "eth_v1_price_only")
    assert eth.get("holdout_pass") is True
    assert "eth_v1_price_only" in doc["holdout_pass_target_ids"]
