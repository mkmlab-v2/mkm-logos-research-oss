from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts/check_opendata_327_draft_hold_v1.py"
FIXTURE = ROOT / "tests/fixtures/opendata_327_policy_slot_hold_v1.json"


def test_hold_fixture_returns_exit_2(tmp_path: Path) -> None:
    out = tmp_path / "hold_report.json"
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--input-json", str(FIXTURE), "--out-json", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 2
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["decision"] == "HOLD"
    assert report["send_gate"] == "HOLD"
    assert report["ready_for_human_review"] is False
    assert len(report["violations"]) >= 1


def test_clean_draft_returns_exit_0(tmp_path: Path) -> None:
    clean_input = tmp_path / "clean.json"
    clean_input.write_text(
        json.dumps(
            {
                "schema": "opendata_327_policy_slot_hold_v1",
                "slots": [
                    {
                        "slot_id": "ok_slot",
                        "text": "근거가 연결된 초안입니다.",
                        "evidence_chunk_ids": ["chunk_01"],
                        "required_fields": {
                            "legal_name": "주식회사 목소리네트워크",
                            "brn": "628-86-01742",
                            "task_id": "opendata327_task1",
                        },
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    out = tmp_path / "ready_report.json"
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--input-json", str(clean_input), "--out-json", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["decision"] == "REVIEW_READY"
    assert report["ready_for_human_review"] is True
    assert report["violations"] == []
