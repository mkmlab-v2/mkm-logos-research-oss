"""build_marketing_weekly_bundle_summary_v1 — summary JSON contract."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/build_marketing_weekly_bundle_summary_v1.py"
TIER = ROOT / "docs/final/artifacts/marketing_ops_cost_tier_v1_latest.json"


def test_build_summary_writes_schema(tmp_path, monkeypatch):
    out = tmp_path / "summary.json"
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--out-json", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "marketing_weekly_bundle_summary_v1"
    assert doc["human_publish_only"] is True
    assert TIER.is_file()


def test_tier_json_has_three_tiers():
    doc = json.loads(TIER.read_text(encoding="utf-8"))
    assert doc["schema"] == "marketing_ops_cost_tier_v1"
    assert set(doc["tiers"].keys()) == {"tier_0", "tier_15", "tier_50"}
