"""RQ-027 commander dev pack ↔ pet bridge KV stub."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_commander_dev_pack_pet_bridge_kv_stub_v1 import build_stub  # noqa: E402
from sync_commander_dev_pack_trust_packet_v2_v1 import build_trust_packet_v2, merge_into_pack  # noqa: E402

PACK_FIXTURE = {
    "schema": "commander_dev_day_pack_v1",
    "hypothesis_tier": "B",
    "research_only": True,
    "non_gating": True,
    "developer_coaching": {"one_line": "검증 우선 [가설]"},
    "energy_pacing": {"summary": "저수면 모드 [가설]"},
    "four_ai_roles_for_dev": {"taeyang": "설계 [가설]"},
    "trust_packet_v2": {"track_wall": {"track_a_trading": "LOCKED"}},
}


def test_trust_packet_v2_sync_layers(tmp_path: Path) -> None:
    trust = build_trust_packet_v2(workspace=ROOT)
    assert trust.get("layers_ref")
    assert trust.get("boundary_ko")
    pack = dict(PACK_FIXTURE)
    merge_into_pack(pack, trust)
    assert pack["trust_packet_v2"].get("synced_at_utc")


def test_pet_stub_separate_channels_and_integrity(tmp_path: Path) -> None:
    pack_path = tmp_path / "pack.json"
    pack_path.write_text(json.dumps(PACK_FIXTURE, ensure_ascii=False), encoding="utf-8")
    slots = ROOT / "docs/final/artifacts/fixtures/pet_companion_memory_slots_demo_fallback_v1.json"
    stub = build_stub(
        pack_path=pack_path,
        slots_path=slots,
        pet_profile_id="pet-demo-001",
        write_bridge_dry=False,
    )
    assert stub["schema"] == "commander_dev_pack_pet_bridge_kv_stub_v1"
    assert stub["commander_to_pet_merge_forbidden"] is True
    assert stub["integrity_check"]["pass"] is True
    assert stub["operator_channel"]["must_not_forward_to_pet_bridge"] is True
    assert stub["pet_target"]["subject_placeholder"] == "[TARGET]"
    assert stub["pet_kv_injection_plan"]["write_mode"] == "stub_only_no_remote_kv"
    assert len(stub["mapping_audit"]) == 10


def test_kv_mirror_writes_local_paths(tmp_path: Path, monkeypatch) -> None:
    import sys

    sys.path.insert(0, str(ROOT / "scripts"))
    from write_commander_dev_pack_pet_kv_mirror_v1 import write_mirror, MIRROR_ROOT  # noqa: E402

    monkeypatch.setattr("write_commander_dev_pack_pet_kv_mirror_v1.MIRROR_ROOT", tmp_path / "mirror")
    monkeypatch.delenv("MKM_PET_KV_REMOTE_WRITE", raising=False)
    stub = {
        "commander_to_pet_merge_forbidden": True,
        "integrity_check": {"pass": True},
        "pet_target": {"profile_id": "pet-demo-001"},
        "pet_kv_injection_plan": {"planned_event_id": "stub-20260605"},
        "pet_bridge_request_dry_run": {"scenario": "health_check"},
        "operator_channel": {"slots": []},
    }
    bridge = {
        "schema": "pet_companion_device_memory_bridge_request_v1",
        "request_id": "req-test",
        "raw_user_question_masked": "[TARGET] stub",
        "memory_context_injection": {"extracted_slots": [{"subject": "[TARGET]", "fact_summary": "x"}]},
    }
    sp = tmp_path / "stub.json"
    bp = tmp_path / "bridge.json"
    sp.write_text(json.dumps(stub, ensure_ascii=False), encoding="utf-8")
    bp.write_text(json.dumps(bridge, ensure_ascii=False), encoding="utf-8")
    out = write_mirror(stub_path=sp, bridge_path=bp, namespace_id="")
    assert out["paths_written"]["coach_event"]
    assert (tmp_path / "mirror" / "coach_events" / "pet-demo-001").is_dir()
    assert out["remote_put"]["coach_event"]["skipped"] is True
