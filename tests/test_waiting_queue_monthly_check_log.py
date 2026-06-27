# @MKM12-METADATA
# Type: Logic
# Purpose: Validate waiting-queue monthly check log JSONL contract.
# Keywords: waiting-queue, monthly-check, jsonl, ops

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


_ROOT = Path(__file__).resolve().parents[1]
_LOG = _ROOT / "docs" / "final" / "artifacts" / "waiting_queue_monthly_check_log.jsonl"


def _rows(path: Path):
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s:
            yield json.loads(s.lstrip("\ufeff"))


def test_waiting_queue_log_exists_and_has_rows() -> None:
    assert _LOG.is_file(), f"missing log: {_LOG}"
    rows = list(_rows(_LOG))
    assert rows, "waiting queue monthly check log must not be empty"


def test_waiting_queue_log_row_contract() -> None:
    rows = list(_rows(_LOG))
    monthly_rows = [r for r in rows if "checked_at_utc" in r]
    assert monthly_rows, "waiting queue log must include at least one monthly-check row"
    for i, row in enumerate(monthly_rows):
        for key in ("checked_at_utc", "bundle_mode", "cross_ref_test", "runner"):
            assert key in row, f"monthly row[{i}] missing key: {key}"
            assert str(row[key]).strip(), f"monthly row[{i}] empty value: {key}"

        datetime.fromisoformat(str(row["checked_at_utc"]).replace("Z", "+00:00"))
        assert row["bundle_mode"] in {"skip_bundle", "full_bundle"}, f"monthly row[{i}] invalid bundle_mode"
        assert row["cross_ref_test"] == "pass", f"monthly row[{i}] cross_ref_test must be pass"
        assert str(row["runner"]) == "scripts/run_waiting_queue_monthly_check.ps1", (
            f"monthly row[{i}] runner mismatch"
        )

        bundle_test = str(row.get("bundle_test", ""))
        if row["bundle_mode"] == "skip_bundle":
            assert bundle_test in {"skipped", "pass"}, f"monthly row[{i}] invalid skip bundle_test"
        else:
            assert bundle_test == "pass", f"monthly row[{i}] full bundle_test must be pass"

    sidecar_rows = [r for r in rows if "checked_at_utc" not in r]
    for i, row in enumerate(sidecar_rows):
        assert str(row.get("schema") or "").strip(), f"sidecar row[{i}] must declare schema"
        assert str(row.get("runner") or "").strip(), f"sidecar row[{i}] must declare runner"


def test_entry07_entry08_cross_ref_summaries_on_disk() -> None:
    p7 = _ROOT / "docs" / "final" / "artifacts" / "entry07_source_hunt_summary_latest.json"
    p8 = _ROOT / "docs" / "final" / "artifacts" / "entry08_source_hunt_summary_latest.json"
    assert p7.is_file(), f"missing {p7}"
    assert p8.is_file(), f"missing {p8}"
    s7 = json.loads(p7.read_text(encoding="utf-8"))
    s8 = json.loads(p8.read_text(encoding="utf-8"))
    assert s7.get("cross_ref_entry") == "ENTRY_07"
    assert s8.get("cross_ref_entry") == "ENTRY_08"
    assert s7.get("ssot_mutation") is False
    assert s8.get("ssot_mutation") is False


def test_waiting_queue_has_entry16_gate_fields_in_recent_rows() -> None:
    rows = list(_rows(_LOG))
    candidates = [r for r in rows if "promotion_gate" in r or "promotion_gate_path" in r]
    assert candidates, "at least one log row must include promotion gate fields"

    latest = candidates[-1]
    assert latest.get("source_hunt_summary") == "pass"
    assert str(latest.get("source_hunt_summary_path", "")).endswith(
        "docs\\final\\artifacts\\entry16_source_hunt_summary.json"
    )
    assert latest.get("promotion_gate") == "pass"
    assert str(latest.get("promotion_gate_path", "")).endswith(
        "docs\\final\\artifacts\\entry16_promotion_gate.json"
    )


def test_waiting_queue_has_deadline_fields_in_recent_rows() -> None:
    rows = list(_rows(_LOG))
    candidates = [r for r in rows if "next_monthly_due_date" in r and "horizon_t90_date" in r]
    assert candidates, "at least one log row must include deadline fields"

    latest = candidates[-1]
    for key in ("next_monthly_due_date", "horizon_t30_date", "horizon_t90_date"):
        value = str(latest.get(key, "")).strip()
        assert value, f"missing {key}"
        datetime.fromisoformat(value)


def test_waiting_queue_has_symbol_lane_gate_fields_in_recent_rows() -> None:
    rows = list(_rows(_LOG))
    candidates = [r for r in rows if "btrack_symbol_lane_gate" in r or "btrack_symbol_lane_gate_path" in r]
    assert candidates, "at least one log row must include symbol lane gate fields"

    latest = candidates[-1]
    assert str(latest.get("btrack_symbol_lane_gate", "")).strip() in {"pass", "skipped"}
    assert str(latest.get("btrack_symbol_lane_gate_path", "")).endswith(
        "reports\\constitution\\btrack_pilot\\symbol_lane_gate_latest.json"
    )


def test_waiting_queue_has_k_shield_metadata_fields_in_recent_rows() -> None:
    rows = list(_rows(_LOG))
    candidates = [
        r
        for r in rows
        if "prophecy_k_shield_candidate" in r or "prophecy_k_shield_candidate_max_drawdown_pct" in r
    ]
    if not candidates:
        return

    latest = candidates[-1]
    assert str(latest.get("prophecy_k_shield_candidate", "")).strip(), "missing prophecy_k_shield_candidate"
    assert latest.get("prophecy_k_shield_candidate_max_drawdown_pct") is not None


def test_waiting_queue_has_regime_switch_sensor_fields_in_recent_rows() -> None:
    rows = list(_rows(_LOG))
    candidates = [
        r
        for r in rows
        if "regime_switch_delta_net_return_pct_sum" in r
        or "regime_switch_delta_profit_factor_weighted" in r
        or "regime_switch_delta_max_drawdown_pct_worst_year" in r
    ]
    if not candidates:
        return

    latest = candidates[-1]
    assert str(latest.get("regime_switch_report_path", "")).endswith(
        "docs\\final\\artifacts\\btc_time_machine_regime_switch_backtest_latest.json"
    )
    advisory = str(latest.get("regime_switch_advisory", "")).strip()
    assert advisory in {
        "prefer_switch_profile",
        "review_switch_profile",
        "mixed_signal_keep_observe",
        "sensor_unavailable",
    }
    assert str(latest.get("regime_switch_advisory_reason", "")).strip()


def test_waiting_queue_post_close_eval_fields_when_present() -> None:
    rows = list(_rows(_LOG))
    candidates = [
        r
        for r in rows
        if "post_close_eval_decision" in r
        or "close_return_pct" in r
        or "predicted_band" in r
    ]
    if not candidates:
        return

    latest = candidates[-1]
    assert latest.get("post_close_eval_decision") in {
        "PENDING_CLOSE",
        "HIT",
        "FAIL",
        "NEUTRAL_DRAW",
    }
    if latest.get("close_return_pct") is not None:
        assert isinstance(latest.get("close_return_pct"), (int, float))
    if latest.get("predicted_band") is not None:
        assert str(latest.get("predicted_band")).strip().upper() in {
            "DOWN_STRONG",
            "UP_STRONG",
            "NEUTRAL",
        }


def test_waiting_queue_has_dual_regime_alert_fields_in_recent_rows() -> None:
    rows = list(_rows(_LOG))
    candidates = [r for r in rows if "dual_regime_alert_level" in r or "dual_regime_alert_reason" in r]
    if not candidates:
        return
    latest = candidates[-1]
    assert str(latest.get("dual_regime_alert_level", "")).strip() in {
        "insufficient_data",
        "state_signal_not_wired",
        "state_clamp_high_tight_mode",
        "state_clamp_active_review_thresholds",
        "state_clamp_stable",
    }
    assert str(latest.get("dual_regime_alert_reason", "")).strip()


def test_waiting_queue_auto_hold_override_priority_fields_when_present() -> None:
    rows = list(_rows(_LOG))
    candidates = [r for r in rows if r.get("auto_hold_promotion") is True]
    if not candidates:
        return
    latest = candidates[-1]
    trig = str(latest.get("override_trigger_type", "")).strip()
    if trig:
        assert trig in {"net_source_fallback", "dual_regime_state_clamp"}
    pri = latest.get("override_priority")
    if pri is not None:
        assert isinstance(pri, (int, float))
    skew = latest.get("override_skew_decision")
    if skew is not None:
        assert str(skew).strip() in {
            "override_skew_net_source_fallback",
            "override_skew_dual_regime_state_clamp",
        }
    skew_threshold = latest.get("override_skew_streak_threshold")
    if skew_threshold is not None:
        assert isinstance(skew_threshold, (int, float))
        assert int(skew_threshold) >= 1
