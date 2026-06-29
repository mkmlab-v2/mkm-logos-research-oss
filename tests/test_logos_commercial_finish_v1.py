from __future__ import annotations

import json
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]


def test_finish_closure_schema() -> None:
    path = _ROOT / "docs/final/artifacts/logos_commercial_finish_closure_v1_latest.json"
    if not path.is_file():
        pytest.skip("finish closure not built yet")
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    assert doc.get("schema") == "logos_commercial_finish_closure_v1"
    assert "checks" in doc


def test_dss_shadow_lane_schema() -> None:
    path = _ROOT / "reports/dss_apocrypha_shadow_lane_v1_latest.json"
    if not path.is_file():
        pytest.skip("dss lane not built yet")
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    assert doc.get("schema") == "dss_apocrypha_shadow_lane_v1"
