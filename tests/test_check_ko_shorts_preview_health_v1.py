"""Preview health check for ko shorts Cursor QA."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.check_ko_shorts_preview_health_v1 import check_ko_shorts_preview_health_v1  # noqa: E402
from scripts.ko_shorts_cursor_ide_qa_lib_v1 import build_preview_html_v1  # noqa: E402


def test_preview_health_passes_on_generated_html(tmp_path: Path) -> None:
    html = tmp_path / "preview.html"
    mp4_name = "ko_shorts_burnin_web_deeply_v1_latest.mp4"
    media = ROOT / "reports" / mp4_name
    if not media.is_file():
        return
    html.write_text(
        build_preview_html_v1(
            [{"case_id": "web_deeply", "mp4_rel": f"reports/{mp4_name}", "cues": []}],
            port=8796,
        ),
        encoding="utf-8",
    )
    report = check_ko_shorts_preview_health_v1(html_path=html, port=8796, require_http=False)
    assert report["ok"] is True
    assert not report["issues"]


def test_preview_health_flags_double_reports_prefix(tmp_path: Path) -> None:
    html = tmp_path / "bad.html"
    html.write_text('<video src="reports/foo.mp4"></video>', encoding="utf-8")
    report = check_ko_shorts_preview_health_v1(html_path=html, port=8796, require_http=False)
    assert report["ok"] is False
    kinds = {i["kind"] for i in report["issues"]}
    assert "double_reports_prefix" in kinds
