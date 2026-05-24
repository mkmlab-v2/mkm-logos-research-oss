"""M20: Health sidecar wired through export, batch, JSONL replay chain."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_send_turn_wire_passes_sidecar_flag():
    from fastapi.testclient import TestClient

    from scripts.compression_token_api_v2_stub import app
    from scripts.mkm_inter_agent_wire_runtime_adapter_v1 import send_turn_wire_v1

    sample = "환자 건강 수면 식사 증상 호흡 피로 회복 체온 임상 바이탈."
    c = TestClient(app)
    sent = send_turn_wire_v1(
        c,
        text=sample,
        session_id="m20-test",
        turn_id=1,
        from_agent="athena",
        to_agent="sentinel",
        use_ko_health_sidecar=True,
    )
    env = sent.get("envelope") or {}
    assert len((env.get("payload") or {}).get("atom_id_sequence") or []) > 1


def test_export_session_health_sidecar():
    from scripts.export_mkm_inter_agent_wire_session_v1 import export_session

    doc = export_session(scenario="health", turns=3, use_ko_health_sidecar=True)
    assert doc.get("ok")
    assert doc.get("use_ko_health_sidecar") is True
    envs = doc.get("envelopes") or []
    assert len(envs) >= 3
    avg = sum(len((r.get("envelope") or {}).get("payload", {}).get("atom_id_sequence") or []) for r in envs) / len(
        envs
    )
    assert avg > 1.0


def test_batch_sidecar_scenarios():
    from scripts.export_mkm_inter_agent_wire_sessions_batch_v1 import export_batch

    doc = export_batch(scenarios=("health", "trading"), turns=2, sidecar_scenarios=("health",))
    assert doc.get("ok")
    health = (doc.get("sessions") or {}).get("health") or {}
    trading = (doc.get("sessions") or {}).get("trading") or {}
    assert health.get("use_ko_health_sidecar") is True
    assert trading.get("use_ko_health_sidecar") is False


def test_m20_batch_chain():
    from scripts.run_mkm_inter_agent_ko_health_sidecar_batch_chain_v1 import run_chain

    doc = run_chain(turns=3)
    assert doc.get("ok")
    assert doc.get("replay_api", {}).get("ok")
