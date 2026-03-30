# @MKM12-METADATA
# Type: Logic
# Purpose: Validate B-Track symbol lane gate/baseline regression artifacts.
# Keywords: btrack, symbol-lane, gate, baseline, regression

from __future__ import annotations

import json
from pathlib import Path


_ROOT = Path(__file__).resolve().parents[1]
_LANE_GATE = _ROOT / "reports" / "constitution" / "btrack_pilot" / "symbol_lane_gate_latest.json"
_LANE_BASELINE = _ROOT / "reports" / "constitution" / "btrack_pilot" / "btrack_symbol_lane_baseline_lock_latest.json"


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_symbol_lane_gate_artifact_contract() -> None:
    assert _LANE_GATE.is_file(), f"missing gate artifact: {_LANE_GATE}"
    gate = _read(_LANE_GATE)
    assert gate.get("schema") == "btrack_symbol_lane_gate_result_v1"
    assert gate.get("decision") in {"pass", "hold"}
    lanes = gate.get("lanes")
    assert isinstance(lanes, dict), "lanes must be object"
    for lane in ("dss_priority", "mixed", "apocrypha_priority"):
        assert lane in lanes, f"missing lane: {lane}"
        payload = lanes[lane]
        assert isinstance(payload, dict), f"{lane} payload must be object"
        assert payload.get("decision") in {"pass", "hold"}, f"{lane} invalid decision"
        metrics = payload.get("metrics")
        assert isinstance(metrics, dict), f"{lane} metrics must be object"
        for key in (
            "count",
            "avg_score_tfidf_like",
            "avg_dss_ratio",
            "dss_presence_rate",
            "contamination_rate",
        ):
            assert key in metrics, f"{lane} missing metric: {key}"


def test_symbol_lane_baseline_contract() -> None:
    assert _LANE_BASELINE.is_file(), f"missing baseline artifact: {_LANE_BASELINE}"
    baseline = _read(_LANE_BASELINE)
    assert baseline.get("schema") == "btrack_symbol_lane_baseline_lock_v1"
    assert baseline.get("baseline_decision") in {"pass", "hold"}
    policy = baseline.get("regression_policy")
    assert isinstance(policy, dict), "regression_policy must be object"
    assert policy.get("require_decision") == "pass"
    assert policy.get("require_lane_decision") == "pass"
    for key in (
        "dss_priority_count_min",
        "mixed_count_min",
        "apocrypha_count_min",
        "dss_priority_avg_dss_ratio_min",
        "mixed_avg_dss_ratio_min",
    ):
        assert key in policy, f"missing regression policy key: {key}"


def test_symbol_lane_regression_floor_guard() -> None:
    gate = _read(_LANE_GATE)
    baseline = _read(_LANE_BASELINE)
    policy = baseline["regression_policy"]

    assert gate.get("decision") == "pass", "overall lane gate decision must be pass"
    lanes = gate["lanes"]
    for lane in ("dss_priority", "mixed", "apocrypha_priority"):
        assert lanes[lane]["decision"] == "pass", f"{lane} decision must be pass"

    dss_metrics = lanes["dss_priority"]["metrics"]
    mixed_metrics = lanes["mixed"]["metrics"]
    apo_metrics = lanes["apocrypha_priority"]["metrics"]

    assert float(dss_metrics["count"]) >= float(policy["dss_priority_count_min"])
    assert float(mixed_metrics["count"]) >= float(policy["mixed_count_min"])
    assert float(apo_metrics["count"]) >= float(policy["apocrypha_count_min"])
    assert float(dss_metrics["avg_dss_ratio"]) >= float(policy["dss_priority_avg_dss_ratio_min"])
    assert float(mixed_metrics["avg_dss_ratio"]) >= float(policy["mixed_avg_dss_ratio_min"])
