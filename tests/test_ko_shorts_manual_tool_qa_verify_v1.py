"""CapCut/Vrew manual QA automated verify tests."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.verify_ko_shorts_manual_tool_qa_v1 import build_verify_report_v1  # noqa: E402


def test_build_verify_report_schema() -> None:
    report = build_verify_report_v1()
    assert report["schema"] == "ko_shorts_manual_tool_qa_verify_v1"
    assert report["send_gate"] == "HOLD"
    assert len(report["checks"]) == 6
    ids = {c["id"] for c in report["checks"]}
    assert "orphan_line" in ids
    assert "netflix_cpl" in ids


def test_verify_cli_writes_artifact(tmp_path: Path) -> None:
    import subprocess

    out = tmp_path / "verify.json"
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/verify_ko_shorts_manual_tool_qa_v1.py"), "--out", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode in (0, 1)
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "ko_shorts_manual_tool_qa_verify_v1"
