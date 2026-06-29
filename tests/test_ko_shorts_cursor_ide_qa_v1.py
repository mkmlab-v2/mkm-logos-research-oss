"""Cursor IDE automated QA for ko shorts burn-in."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.ko_shorts_cursor_ide_qa_lib_v1 import (  # noqa: E402
    build_cursor_ide_qa_report_v1,
    check_orphan_cues_v1,
    check_p1_anchor_sync_v1,
)


def test_p1_anchor_sync_passes_on_fixture_segments() -> None:
    p1 = [
        {
            "start": "00:00:00.00",
            "end": "00:00:02.00",
            "token_start": 0,
            "start_source": "aligned_token",
        }
    ]
    result = check_p1_anchor_sync_v1(p1)
    assert result["auto_pass"] is True


def test_build_cursor_qa_report_schema() -> None:
    report = build_cursor_ide_qa_report_v1()
    assert report["schema"] == "ko_shorts_cursor_ide_qa_v1"
    assert report["send_gate"] == "HOLD"
    assert "preview_url" in report
    assert (ROOT / "reports/ko_shorts_cursor_preview_v1.html").is_file()


def test_orphan_detect() -> None:
    cues = [{"text": "줍니다."}]
    assert check_orphan_cues_v1(cues)["orphan_count"] == 1


def test_preview_html_video_src_matches_reports_http_root() -> None:
    from scripts.ko_shorts_cursor_ide_qa_lib_v1 import build_preview_html_v1

    html = build_preview_html_v1(
        [
            {
                "case_id": "web_deeply",
                "mp4_rel": "reports/ko_shorts_burnin_web_deeply_v1_latest.mp4",
                "cues": [],
            }
        ]
    )
    assert 'src="ko_shorts_burnin_web_deeply_v1_latest.mp4"' in html
    assert 'src="reports/' not in html


def test_cursor_qa_cli(tmp_path: Path) -> None:
    import subprocess

    out = tmp_path / "qa.json"
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/run_ko_shorts_cursor_ide_qa_v1.py"), "--out", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode in (0, 1)
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "ko_shorts_cursor_ide_qa_v1"
