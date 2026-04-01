import json
from pathlib import Path

from scripts import broadcast_fact_safe_multilens_brief as brief
from scripts.broadcast_fact_safe_multilens_brief import _extract, _validate_lock_contract


def test_extract_key_value_from_markdown_line():
    md = "- reliability_badge: HIGH\n- gate_reason: monthly_check_gate\n"
    assert _extract(md, "reliability_badge") == "HIGH"
    assert _extract(md, "gate_reason") == "monthly_check_gate"


def test_extract_returns_none_when_missing():
    md = "- other: value\n"
    assert _extract(md, "history net_delta") is None


def test_extract_trims_value():
    md = "- net:   +12.3400   \n"
    assert _extract(md, "net") == "+12.3400"


def test_validate_lock_contract_requires_lock_when_low():
    ok, err = _validate_lock_contract(
        {
            "reliability_badge": "LOW",
            "high_reliability_decision": "HOLD",
            "price_output_locked": False,
            "lock_reason": None,
        }
    )
    assert ok is False
    assert err == "low_or_hold_requires_price_output_locked_true"


def test_validate_lock_contract_passes_when_locked_with_reason():
    ok, err = _validate_lock_contract(
        {
            "reliability_badge": "LOW",
            "high_reliability_decision": "HOLD",
            "price_output_locked": True,
            "lock_reason": "low_or_hold_mode_price_output_forbidden",
        }
    )
    assert ok is True
    assert err is None


def test_monthly_outlook_includes_k_shield_fields(tmp_path):
    prophecy = tmp_path / "prophecy.json"
    prophecy.write_text(
        json.dumps(
            {
                "meta": {
                    "k_shield_candidate_name": "k_shield_h1_soft",
                    "k_shield_candidate_net_return_pct": -6.383742,
                    "k_shield_candidate_profit_factor": 0.840615,
                    "k_shield_candidate_max_drawdown_pct": 8.285629,
                },
                "risk_profile": {},
                "months": [
                    {
                        "month": 1,
                        "phase": "기준선/탐색",
                        "kospi": {"direction": "중립", "down_pct": 34},
                        "btc": {"direction": "중립", "down_pct": 35},
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    old_path = brief.MONTHLY_PROPHECY_JSON
    old_datetime = brief.datetime
    try:
        brief.MONTHLY_PROPHECY_JSON = prophecy

        class _FakeNow:
            @staticmethod
            def now(_tz):
                return old_datetime(2026, 1, 15, tzinfo=_tz)

        brief.datetime = _FakeNow
        out = brief._monthly_outlook_for_now()
        assert out["k_shield_candidate_name"] == "k_shield_h1_soft"
        assert out["k_shield_candidate_max_drawdown_pct"] == 8.285629
    finally:
        brief.MONTHLY_PROPHECY_JSON = old_path
        brief.datetime = old_datetime


def test_latest_waiting_log_exposes_regime_switch_advisory(tmp_path):
    log = tmp_path / "waiting.jsonl"
    log.write_text(
        json.dumps(
            {
                "checked_at_utc": "2026-03-31T00:00:00Z",
                "regime_switch_advisory": "prefer_switch_profile",
                "regime_switch_advisory_reason": "delta_positive_net_pf_and_lower_mdd",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    old_log = brief.WAITING_LOG
    try:
        brief.WAITING_LOG = log
        row = brief._latest_waiting_log()
        assert row.get("regime_switch_advisory") == "prefer_switch_profile"
        assert row.get("regime_switch_advisory_reason") == "delta_positive_net_pf_and_lower_mdd"
    finally:
        brief.WAITING_LOG = old_log


def test_main_writes_regime_switch_advisory_fields(tmp_path: Path, monkeypatch):
    brief_md = tmp_path / "brief.md"
    brief_md.write_text(
        "\n".join(
            [
                "- reliability_badge: MID",
                "- high_reliability_decision: PASS",
                "- gate_reason: monthly_check_gate",
                "- net: -0.12",
                "- history samples: 10",
                "- history net_delta: -1.1",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    waiting_log = tmp_path / "waiting.jsonl"
    waiting_log.write_text(
        json.dumps(
            {
                "regime_switch_advisory": "review_switch_profile",
                "regime_switch_advisory_reason": "at_least_one_delta_degraded",
                "overlap_drift_alert": False,
                "overlap_drift_alert_threshold": -0.05,
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    prophecy = tmp_path / "prophecy.json"
    prophecy.write_text(json.dumps({"months": [], "meta": {}}, ensure_ascii=False) + "\n", encoding="utf-8")
    trinity = tmp_path / "trinity_scoring_distribution_latest.json"
    trinity.write_text(
        json.dumps(
            {
                "dual_regime_state": {
                    "all": {"sample_size": 5, "top_source": "none", "clamp_rate": 0.0},
                    "advisory": {"decision": "state_signal_not_wired", "reason": "top_source_none_and_present_rate_low"},
                },
                "auto_hold_overrides": {
                    "all": {"count": 7, "top_trigger": "net_source_fallback"},
                    "advisory": {"decision": "override_skew_net_source_fallback", "reason": "top_trigger_net_source_fallback_ratio_ge_0.7"},
                },
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    out_dir = tmp_path / "out"
    out_md = out_dir / "broadcast.md"
    out_json = out_dir / "broadcast.json"

    old_brief = brief.FACT_SAFE_BRIEF
    old_waiting = brief.WAITING_LOG
    old_prophecy = brief.MONTHLY_PROPHECY_JSON
    old_out_dir = brief.OUT_DIR
    old_out_md = brief.OUT_MD
    old_out_json = brief.OUT_JSON
    old_trinity = brief.TRINITY_SCORING_DISTRIBUTION_JSON
    try:
        brief.FACT_SAFE_BRIEF = brief_md
        brief.WAITING_LOG = waiting_log
        brief.MONTHLY_PROPHECY_JSON = prophecy
        brief.OUT_DIR = out_dir
        brief.OUT_MD = out_md
        brief.OUT_JSON = out_json
        brief.TRINITY_SCORING_DISTRIBUTION_JSON = trinity
        monkeypatch.setattr("sys.argv", ["prog"])
        rc = brief.main()
        assert rc == 0
        payload = json.loads(out_json.read_text(encoding="utf-8"))
        assert payload.get("regime_switch_advisory") == "review_switch_profile"
        assert payload.get("regime_switch_advisory_reason") == "at_least_one_delta_degraded"
        assert payload.get("dual_regime_state_advisory", {}).get("decision") == "state_signal_not_wired"
        assert payload.get("auto_hold_override_advisory", {}).get("decision") == "override_skew_net_source_fallback"
        md_text = out_md.read_text(encoding="utf-8")
        assert "- regime_switch_advisory: review_switch_profile" in md_text
        assert "- regime_switch_advisory_reason: at_least_one_delta_degraded" in md_text
        assert "- dual_regime_state_advisory:" in md_text
        assert "- auto_hold_override_advisory:" in md_text
    finally:
        brief.FACT_SAFE_BRIEF = old_brief
        brief.WAITING_LOG = old_waiting
        brief.MONTHLY_PROPHECY_JSON = old_prophecy
        brief.OUT_DIR = old_out_dir
        brief.OUT_MD = old_out_md
        brief.OUT_JSON = old_out_json
        brief.TRINITY_SCORING_DISTRIBUTION_JSON = old_trinity
