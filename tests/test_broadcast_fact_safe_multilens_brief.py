import json

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
