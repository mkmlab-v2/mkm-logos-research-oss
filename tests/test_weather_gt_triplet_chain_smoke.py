# @MKM12-METADATA
# Type: Logic
# Purpose: Minimal weather GT triplet smoke tests for CI stability.

from __future__ import annotations

from pathlib import Path


_ROOT = Path(__file__).resolve().parents[1]


def test_weather_gt_triplet_smoke_scripts_or_fixtures_present() -> None:
    """CI에서 날씨 triplet 관련 자산이 완전히 비어있지 않은지 최소 확인."""
    candidates = [
        _ROOT / "tests" / "fixtures" / "weather_ground_truth_rows_v1.sample.jsonl",
        _ROOT / "tests" / "fixtures" / "btc_smoke_daily.csv",
        _ROOT / "scripts" / "run_weather_gt_to_prophecy_triplet_chain_v1.py",
        _ROOT / "scripts" / "build_weather_triplet_registry_v1.py",
    ]
    assert any(p.exists() for p in candidates), "weather triplet smoke assets are missing"


def test_weather_gt_triplet_smoke_artifacts_dir_exists() -> None:
    artifacts_dir = _ROOT / "docs" / "final" / "artifacts"
    assert artifacts_dir.is_dir(), f"missing artifacts dir: {artifacts_dir}"
