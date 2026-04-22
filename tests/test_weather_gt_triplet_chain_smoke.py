# @MKM12-METADATA
# Type: Logic
# Purpose: Minimal weather GT triplet smoke tests for CI stability.

from __future__ import annotations

from pathlib import Path


_ROOT = Path(__file__).resolve().parents[1]


def test_weather_gt_triplet_smoke_scripts_or_fixtures_present() -> None:
    """파일 레이아웃 최소 가드: tests/smoke target이 실행 가능한 루트 구조인지 확인."""
    assert (_ROOT / "scripts").is_dir(), "missing scripts dir"


def test_weather_gt_triplet_smoke_artifacts_dir_exists() -> None:
    artifacts_dir = _ROOT / "docs" / "final" / "artifacts"
    assert artifacts_dir.is_dir(), f"missing artifacts dir: {artifacts_dir}"
