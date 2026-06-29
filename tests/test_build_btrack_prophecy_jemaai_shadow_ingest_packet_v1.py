"""Tests for btrack prophecy jemaai shadow ingest packet builder."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_btrack_prophecy_jemaai_shadow_ingest_packet_v1.py"


def _import_main():
    import importlib.util

    spec = importlib.util.spec_from_file_location("shadow_ingest_pkt", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod.main


def test_refuses_when_auto_promote_not_ready(tmp_path: Path) -> None:
    gates = tmp_path / "gates.json"
    gates.write_text(
        json.dumps({"auto_promote_ready": False, "strict_passed": True}),
        encoding="utf-8",
    )
    go = tmp_path / "go.json"
    go.write_text(json.dumps({"go_no_go": "NO_GO"}), encoding="utf-8")
    main = _import_main()
    rc = main(
        [
            "--gates-json",
            str(gates),
            "--go-no-go-json",
            str(go),
            "--out-json",
            str(tmp_path / "out.json"),
        ]
    )
    assert rc == 2


def test_builds_packet_when_gates_ready(tmp_path: Path) -> None:
    gates = tmp_path / "gates.json"
    gates.write_text(
        json.dumps(
            {
                "auto_promote_ready": True,
                "strict_passed": True,
                "strict_pass_streak": 6,
                "combined_all_passed": False,
                "outcome_class": "pass_candidate",
                "promotion_recommendation": "auto_promote_ready",
            }
        ),
        encoding="utf-8",
    )
    go = tmp_path / "go.json"
    go.write_text(json.dumps({"go_no_go": "NO_GO", "risk_mode": "LOCKED_MODE"}), encoding="utf-8")
    out = tmp_path / "packet.json"
    main = _import_main()
    rc = main(
        [
            "--gates-json",
            str(gates),
            "--go-no-go-json",
            str(go),
            "--human-review-json",
            str(tmp_path / "no_human_review.json"),
            "--out-json",
            str(out),
        ]
    )
    assert rc == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "btrack_prophecy_jemaai_shadow_ingest_packet_v1"
    assert doc["research_only"] is True
    assert doc["ingest_ready"] is False
    pe = doc["public_event_v1"]
    assert pe["schema_version"] == "public-event.v1"
    assert pe.get("active_character_id") == "bear_shield"
    assert pe["public_signal_direction"] in ("HOLD", "WATCH")
    assert doc["explicit_hold"]["order_routing"] is False
