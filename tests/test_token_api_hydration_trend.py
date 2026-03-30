# @MKM12-METADATA
# Type: Logic
# Purpose: Validate token API hydration trend artifacts.
# Keywords: token-api, hydration, trend, jsonl

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


_ROOT = Path(__file__).resolve().parents[1]
_LOG = _ROOT / "reports" / "constitution" / "btrack_pilot" / "token_api_hydration_mix_log.jsonl"
_TREND = _ROOT / "reports" / "constitution" / "btrack_pilot" / "token_api_hydration_trend_latest.json"


def _rows(path: Path):
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s:
            yield json.loads(s.lstrip("\ufeff"))


def test_token_api_hydration_log_contract() -> None:
    assert _LOG.is_file(), f"missing log: {_LOG}"
    rows = list(_rows(_LOG))
    assert rows, "hydration log must not be empty"
    latest = rows[-1]
    assert latest.get("schema") == "token_api_hydration_mix_log_v1"
    datetime.fromisoformat(str(latest.get("ts_utc")).replace("Z", "+00:00"))
    assert int(latest.get("total_examples", -1)) >= 0
    assert 0.0 <= float(latest.get("live_ratio", -1)) <= 1.0
    assert isinstance(latest.get("metrics_mode_counts"), dict)


def test_token_api_hydration_trend_contract() -> None:
    assert _TREND.is_file(), f"missing trend summary: {_TREND}"
    d = json.loads(_TREND.read_text(encoding="utf-8"))
    assert d.get("schema") == "token_api_hydration_trend_v1"
    datetime.fromisoformat(str(d.get("ts_utc")).replace("Z", "+00:00"))
    assert int(d.get("window_days", -1)) == 7
    assert int(d.get("row_count_total", -1)) >= int(d.get("row_count_window", -1)) >= 0
    assert 0.0 <= float(d.get("latest_live_ratio", -1)) <= 1.0
    assert 0.0 <= float(d.get("avg_live_ratio_7d", -1)) <= 1.0
    assert isinstance(d.get("latest_metrics_mode_counts"), dict)
