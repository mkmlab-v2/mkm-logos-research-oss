"""Tests for productive burn bundle builder."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATCH = ROOT / "scripts" / "sandbox" / "patch_gcp_burn_source_v1.py"
FILLS_CACHE = ROOT / "reports" / "btrack_fills_daily_feature_cache_v1_latest.json"


def test_build_bundle_all_productive(tmp_path: Path) -> None:
    if not FILLS_CACHE.is_file():
        return
    out = tmp_path / "bundle.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(PATCH),
            "--lane",
            "all_productive",
            "--asset-rag-calls",
            "2",
            "--cross-lens-calls",
            "2",
            "--fills-calls",
            "4",
            "--fills-repeat",
            "1",
            "--export-bundle",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    bundle = json.loads(out.read_text(encoding="utf-8"))
    assert bundle["schema"] == "mkm_productive_burn_bundle_v1"
    assert bundle["track_wall"] == "btrack_research_only"
    assert bundle["total_prompts"] >= 4
    lanes = bundle["lanes"]
    assert "asset_rag" in lanes
    assert "btrack_fills_daily" in lanes
    first = lanes["btrack_fills_daily"][0]
    assert "[HYPO]" in first["prompt"]
    assert "INPUT_JSON" in first["prompt"]
