"""Smoke tests for multilens equal-weight 3-arm sandbox."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.run_multilens_equal_weight_sandbox_3arm_v1 import (
    build_report,
    sandbox_3arm_catalog,
)


def test_sandbox_catalog_has_three_arms():
    cat = sandbox_3arm_catalog("kospi")
    assert set(cat) == {
        "sandbox_arm_a_baseline",
        "sandbox_arm_b_equal_cultural_3",
        "sandbox_arm_c_equal_cultural_plus_science",
    }
    b = cat["sandbox_arm_b_equal_cultural_3"]["weights"]
    assert abs(b["logos_non_gating"] - 1 / 3) < 0.02


def test_build_report_schema():
    stub_leg = {
        "instrument": "kospi",
        "window": {},
        "arms": [],
        "evaluation": {},
    }
    doc = build_report(kospi=stub_leg, btc=stub_leg)
    assert doc["schema"] == "multilens_equal_weight_sandbox_3arm_v1"
    assert doc["research_only"] is True


def test_latest_json_if_present():
    path = Path("reports/multilens_equal_weight_sandbox_3arm_v1_latest.json")
    if not path.is_file():
        return
    doc = json.loads(path.read_text(encoding="utf-8"))
    assert doc.get("schema") == "multilens_equal_weight_sandbox_3arm_v1"
    for leg in ("kospi", "btc"):
        assert leg in doc.get("legs", {})
        assert len(doc["legs"][leg].get("arms", [])) == 3
