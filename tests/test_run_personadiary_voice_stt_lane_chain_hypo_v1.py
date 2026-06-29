"""PersonaDiary voice STT audit + lane chain v1 [HYPO]."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CHAIN = ROOT / "scripts/run_personadiary_voice_stt_lane_chain_hypo_v1.py"
CLASSIFY = ROOT / "scripts/classify_personadiary_voice_lane_hypo_v1.py"
FIXTURE = ROOT / "tests/fixtures/personadiary_voice_transcript_hypo_v1.example.json"


def test_build_paste_stt_audit_row_validates() -> None:
    sys.path.insert(0, str(ROOT / "scripts"))
    from build_personadiary_stt_audit_row_hypo_v1 import (  # noqa: E402
        build_paste_stt_audit_row,
        validate_stt_audit_row,
    )

    row = build_paste_stt_audit_row(
        event_id="00000000-0000-4000-8000-000000000099",
        transcript="테스트 전사",
        session_id="pd-test",
    )
    validate_stt_audit_row(row, ROOT / "docs/final/schemas/stt_routing_audit_log_v1.schema.json")
    assert row["route"] == "local"
    assert row["chars_out"] == len("테스트 전사")


def test_build_webspeech_stt_audit_row_validates() -> None:
    sys.path.insert(0, str(ROOT / "scripts"))
    from build_personadiary_stt_audit_row_hypo_v1 import (  # noqa: E402
        build_webspeech_stt_audit_row,
        validate_stt_audit_row,
    )

    row = build_webspeech_stt_audit_row(
        event_id="00000000-0000-4000-8000-000000000099",
        transcript="마이크 전사 테스트",
        session_id="pd-test",
        audio_duration_ms=3200,
    )
    validate_stt_audit_row(row, ROOT / "docs/final/schemas/stt_routing_audit_log_v1.schema.json")
    assert row["route"] == "local"
    assert row["audio_duration_ms"] == 3200
    assert "webspeech" in row["hypothesis_tag"]


@pytest.mark.skipif(not CHAIN.is_file(), reason="chain script missing")
def test_voice_stt_lane_chain_links_event_id(tmp_path: Path) -> None:
    stt_out = tmp_path / "stt.jsonl"
    class_out = tmp_path / "class.json"
    cmd = [
        sys.executable,
        str(CHAIN),
        "--transcript-json",
        str(FIXTURE),
        "--append-stt-audit",
        "--stt-audit-out",
        str(stt_out),
        "--classification-out",
        str(class_out),
    ]
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads(class_out.read_text(encoding="utf-8"))
    assert doc["stt_audit_linked"] is True
    assert doc["stt_event_id"] == doc["stt_audit_row"]["event_id"]
    lines = stt_out.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row["event_id"] == doc["stt_event_id"]


@pytest.mark.skipif(not CLASSIFY.is_file(), reason="classify script missing")
def test_classify_embeds_stt_audit_row(tmp_path: Path) -> None:
    cmd = [
        sys.executable,
        str(CLASSIFY),
        "--transcript-json",
        str(FIXTURE),
        "--out-json",
        str(tmp_path / "out.json"),
    ]
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads((tmp_path / "out.json").read_text(encoding="utf-8"))
    assert doc.get("stt_audit_row")
    assert doc["stt_audit_linked"] is True
