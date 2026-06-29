"""Alignment backend spike + segment decision tests."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_ko_shorts_segment_backend_decision_v1 import build_decision_report_v1  # noqa: E402
from scripts.ko_shorts_alignment_backend_lib_v1 import word_timing_stats_v1  # noqa: E402


def test_word_timing_stats_empty() -> None:
    assert word_timing_stats_v1([])["word_count"] == 0


def test_build_decision_report_schema() -> None:
    report = build_decision_report_v1()
    assert report["schema"] == "ko_shorts_segment_backend_decision_v1"
    assert report["send_gate"] == "HOLD"
    assert report["recommendation"]["segment_default_backend"] == "semantic_chunk_ko_v1"
    assert report["recommendation"]["kssds_adopt_default"] is False


def test_decision_cli_writes_artifact(tmp_path: Path) -> None:
    import subprocess

    out = tmp_path / "decision.json"
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_ko_shorts_segment_backend_decision_v1.py"), "--out", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "ko_shorts_segment_backend_decision_v1"
