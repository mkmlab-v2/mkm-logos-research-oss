from pathlib import Path

from scripts import generate_2026_monthly_kospi_btc_prophecy as monthly_prophecy
from scripts.generate_2026_monthly_kospi_btc_prophecy import _adjust_for_hold, _sasang_external_adjust, _sasang_external_profile


def test_adjust_for_hold_shifts_to_defensive():
    up, neutral, down = _adjust_for_hold(40, 30, 30, True, momentum_score=0.5)
    assert up == 36
    assert neutral == 30
    assert down == 34


def test_adjust_for_hold_keeps_values_when_not_hold():
    up, neutral, down = _adjust_for_hold(40, 30, 30, False, momentum_score=0.5)
    assert (up, neutral, down) == (40, 30, 30)


def test_sasang_external_meltup_shock_follows_momentum_not_mean_reversion():
    """Large positive prior month must not flip tilt negative solely due to shock threshold."""
    profile = _sasang_external_profile()
    up, neutral, down = (24, 34, 42)
    _, _, _, meta = _sasang_external_adjust(
        up,
        neutral,
        down,
        phase="압박/방어",
        prev_ret=20.5,
        roll_abs_3m=19.5,
        profile=profile,
    )
    assert meta["shock_mode"] is True
    assert meta["prev_ret_pct"] > 0
    assert float(meta["tilt"]) > 0.0


def test_sasang_external_crash_shock_keeps_mean_reversion_sign():
    profile = _sasang_external_profile()
    up, neutral, down = (34, 36, 30)
    _, _, _, meta = _sasang_external_adjust(
        up,
        neutral,
        down,
        phase="기준선/탐색",
        prev_ret=-12.0,
        roll_abs_3m=8.0,
        profile=profile,
    )
    assert meta["shock_mode"] is True
    assert meta["prev_ret_pct"] < 0


def test_generate_sets_price_lock_in_hold_mode(tmp_path):
    empty_json = tmp_path / "empty.json"
    empty_json.write_text("{}", encoding="utf-8")
    empty_jsonl = tmp_path / "empty.jsonl"
    empty_jsonl.write_text("", encoding="utf-8")

    old_gate = monthly_prophecy.GATE_JSON
    old_waiting = monthly_prophecy.WAITING_LOG
    old_sweep = monthly_prophecy.BTC_SWEEP
    old_kpi_glob = monthly_prophecy.KPI_JSONL_GLOB
    try:
        monthly_prophecy.GATE_JSON = Path(empty_json)
        monthly_prophecy.WAITING_LOG = Path(empty_jsonl)
        monthly_prophecy.BTC_SWEEP = Path(empty_json)
        monthly_prophecy.KPI_JSONL_GLOB = Path(tmp_path / "kpi_snapshot_*.jsonl")
        doc = monthly_prophecy.generate()
        assert doc["meta"]["price_output_locked"] is True
        assert doc["meta"]["lock_reason"] == "low_or_hold_mode_price_output_forbidden"
        assert doc["meta"]["core_decision"] in {"HOLD", "PASS_LONG", "PASS_SHORT"}
        assert "core_contract_version" in doc["meta"]
        assert "k_shield_candidate_name" in doc["meta"]
        assert doc["meta"]["engine_scope"] == "monthly_prophecy_generation_only"
        assert doc["meta"]["myeongri_verification_engine"] == "project-0-workspace-athena-manseryeok.verify_saju_date"
        assert doc["meta"]["calendar_source_type"] == "external_standard_required"
        assert doc["meta"]["calendar_source_name"] == "standard_rabbinic_calendar"
        assert doc["meta"]["decision_driver_policy"] == "prefer_observed_lever_over_symbolic_lens"
        assert doc["meta"]["scoring_rule"]["labels"]["neutral_draw"] == "NEUTRAL_DRAW"
        assert doc["meta"]["scoring_rule"]["hit_threshold_pct"] == -0.8
        assert doc["meta"]["scoring_rule"]["fail_threshold_pct"] == 1.5
        assert len(doc["meta"]["observed_lever_priority"]) >= 3
        assert "risk_profile" in doc
        assert doc["risk_profile"]["mode"] == "LOCKED_MODE"
        assert doc["risk_profile"]["position_scale_cap"] <= 0.2
        assert doc["risk_profile"]["core_decision"] == doc["meta"]["core_decision"]
        first = doc["months"][0]
        assert "price" not in first["kospi"]
        assert "price" not in first["btc"]
    finally:
        monthly_prophecy.GATE_JSON = old_gate
        monthly_prophecy.WAITING_LOG = old_waiting
        monthly_prophecy.BTC_SWEEP = old_sweep
        monthly_prophecy.KPI_JSONL_GLOB = old_kpi_glob
