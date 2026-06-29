"""PersonaDiary voice → 4-lane classifier v1 [HYPO]."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from classify_personadiary_voice_lane_hypo_v1 import (  # noqa: E402
    classify_voice_transcript,
    load_transcript_json,
)

FIXTURE = ROOT / "tests/fixtures/personadiary_voice_transcript_hypo_v1.example.json"


def test_fixture_loads() -> None:
    loaded = load_transcript_json(FIXTURE)
    assert "숏폼" in loaded["text"]
    assert loaded["active_lane_hint"] == "mind"


def test_classify_fixture_segments() -> None:
    loaded = load_transcript_json(FIXTURE)
    out = classify_voice_transcript(
        loaded["text"],
        active_lane_hint=loaded.get("active_lane_hint"),
        stt_event_id=loaded.get("stt_event_id"),
    )
    assert out["schema"] == "personadiary_voice_lane_classification_hypo_v1"
    assert len(out["segments"]) >= 3
    lanes = [s["lane"] for s in out["segments"]]
    assert "work" in lanes
    assert "rest" in lanes
    assert out["mind_red_flag_tier"] == "watch"
    assert out["human_gate_required"] is True


def test_work_lane_priority() -> None:
    out = classify_voice_transcript("오늘 회의 두 번 있고 마감이 급해요.")
    assert out["segments"][0]["lane"] == "work"


def test_forbidden_consumer_copy_blocked() -> None:
    out = classify_voice_transcript("오늘 운세가 좋대요.")
    seg = out["segments"][0]
    assert seg["blocked"] is True
    assert out["mind_red_flag_tier"] == "blocked"
    assert out["forbidden_blocked_count"] == 1


def test_clinical_soap_language_blocked() -> None:
    out = classify_voice_transcript("SOAP 주관적: 두통 있음.")
    seg = out["segments"][0]
    assert seg["blocked"] is True
    assert any("clinical_forbidden" in v for v in seg.get("violation_codes", []))


def test_cli_fixture_exit_zero(tmp_path: Path) -> None:
    import subprocess

    out_path = tmp_path / "classification.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/classify_personadiary_voice_lane_hypo_v1.py"),
            "--transcript-json",
            str(FIXTURE),
            "--out-json",
            str(out_path),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(out_path.read_text(encoding="utf-8"))
    assert doc["segments"]
