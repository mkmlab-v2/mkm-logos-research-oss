"""Smoke test for BTC decouple spike v2."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_decouple_spike_v2_runs_and_schema() -> None:
    cp = subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_btrack_btc_decouple_spike_v2.py")],
        cwd=str(ROOT),
        check=False,
    )
    assert cp.returncode == 0
    out = ROOT / "reports/btrack_btc_decouple_spike_v2_latest.json"
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "btrack_btc_decouple_spike_v2"
    assert doc["research_only"] is True
    assert doc["baseline_btc"]["n_evaluated"] >= 1
    policy_ids = {p["policy_id"] for p in doc["policies"]}
    assert "P1_decouple_bear_to_neutral" in policy_ids
    assert "P2_decouple_bear_to_bull" in policy_ids
    spec = ROOT / "docs/final/artifacts/btrack_btc_decouple_spike_v2_spec_v1.json"
    assert spec.is_file()
