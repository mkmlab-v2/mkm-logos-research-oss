from pathlib import Path

from scripts import generate_2026_monthly_kospi_btc_prophecy as monthly_prophecy
from scripts.generate_2026_monthly_kospi_btc_prophecy import _adjust_for_hold


def test_adjust_for_hold_shifts_to_defensive():
    up, neutral, down = _adjust_for_hold(40, 30, 30, True)
    assert up == 36
    assert neutral == 30
    assert down == 34


def test_adjust_for_hold_keeps_values_when_not_hold():
    up, neutral, down = _adjust_for_hold(40, 30, 30, False)
    assert (up, neutral, down) == (40, 30, 30)


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
