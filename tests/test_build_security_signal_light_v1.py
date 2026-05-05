from __future__ import annotations

import scripts.build_security_signal_light_v1 as mod


def _snap(meta: dict, reasons: list | None = None) -> dict:
    return {"summary": {"meta": meta, "reasons": reasons or []}}


def test_build_signal_red_when_secret_gate_not_ok() -> None:
    out = mod.build_signal(_snap({"secret_exposure_gate_ok": False, "automation_ops_ready": True, "a_track_go_nogo": "GO"}))
    assert out["signal"] == "RED"
    assert "BLOCKED" in out["one_line_status"]
    assert out["summary"]["secret_exposure_gate_ok"] is False


def test_build_signal_amber_when_ops_not_ready() -> None:
    out = mod.build_signal(_snap({"secret_exposure_gate_ok": True, "automation_ops_ready": False, "a_track_go_nogo": "GO"}))
    assert out["signal"] == "AMBER"
    assert "ops_ready=NO" in out["one_line_status"]


def test_build_signal_green_when_all_ok_and_go() -> None:
    out = mod.build_signal(_snap({"secret_exposure_gate_ok": True, "automation_ops_ready": True, "a_track_go_nogo": "GO"}))
    assert out["signal"] == "GREEN"
    assert "SECURITY=GREEN" in out["one_line_status"]


def test_build_signal_amber_when_go_nogo_not_go_but_ops_ok() -> None:
    out = mod.build_signal(_snap({"secret_exposure_gate_ok": True, "automation_ops_ready": True, "a_track_go_nogo": "HOLD"}))
    assert out["signal"] == "AMBER"
    assert out["summary"]["a_track_go_nogo"] == "HOLD"


def test_build_signal_schema_and_reason_count() -> None:
    out = mod.build_signal(_snap({"secret_exposure_gate_ok": True, "automation_ops_ready": False, "a_track_go_nogo": "GO"}, ["tasks_not_ok"]))
    assert out["schema"] == "security_signal_light_v1"
    assert out["summary"]["reason_count"] == 1
    assert out["summary"]["reasons"] == ["tasks_not_ok"]
