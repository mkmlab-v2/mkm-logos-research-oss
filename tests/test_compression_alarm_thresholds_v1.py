# @MKM12-METADATA
# Type: Logic
# Purpose: Compression KPI alarm thresholds contract (bench floor 0.47).
# Keywords: compression, alarm, bench-floor, rq-016

from __future__ import annotations

import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_THRESH = _ROOT / "docs" / "final" / "artifacts" / "compression_alarm_thresholds_v1.json"
_KPI = _ROOT / "reports" / "constitution" / "btrack_pilot" / "ultra_compression_kpi_summary_latest.json"


def _load(path: Path) -> dict:
    assert path.is_file(), f"missing artifact: {path}"
    return json.loads(path.read_text(encoding="utf-8"))


def _bench_floor_alarm_reasons(active: dict, thr: dict) -> list[str]:
    """Mirror send_compression_kpi_alarm_if_needed.ps1 bench-floor branch."""
    reasons: list[str] = []
    if not thr.get("alarm_if_bench_saving_floor_false", True):
        return reasons
    if "bench_saving_floor_ok" not in active:
        return reasons
    if not active["bench_saving_floor_ok"]:
        floor = thr.get("bench_saving_floor_min", 0.47)
        reasons.append(f"bench_saving_floor_ok=false (RQ-016 floor={floor})")
    return reasons


def test_compression_alarm_thresholds_contract() -> None:
    thr = _load(_THRESH)
    assert thr.get("bench_saving_floor_min") == 0.47
    assert thr.get("track_a_promoted_policy_min") == 0.47
    assert thr.get("suggested_policy_floor_token_saving_rate") == 0.47
    assert thr.get("alarm_if_bench_saving_floor_false") is True


def test_active_kpi_bench_floor_ok_when_promoted() -> None:
    kpi = _load(_KPI)
    active = kpi["active_kpi"]
    thr = _load(_THRESH)
    assert active.get("bench_saving_floor_ok") is True
    assert _bench_floor_alarm_reasons(active, thr) == []


def test_bench_floor_alarm_fires_when_ok_false() -> None:
    thr = _load(_THRESH)
    active = {"bench_saving_floor_ok": False, "global_token_saving_rate": 0.40}
    reasons = _bench_floor_alarm_reasons(active, thr)
    assert len(reasons) == 1
    assert "bench_saving_floor_ok=false" in reasons[0]
    assert "0.47" in reasons[0]
