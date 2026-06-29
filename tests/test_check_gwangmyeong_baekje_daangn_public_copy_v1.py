"""Gate tests for gwangmyeong_baekje daangn public copy."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_build_and_gate_exit_zero() -> None:
    build = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "build_gwangmyeong_baekje_daangn_paste_card_v1.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert build.returncode == 0, build.stderr

    gate = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_gwangmyeong_baekje_daangn_public_copy_v1.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert gate.returncode == 0, gate.stderr
    assert "OK:" in gate.stdout

    html = ROOT / "reports" / "demo" / "gwangmyeong_baekje_daangn_paste_assistant_v1.html"
    assert html.is_file()
    assert "SEND_GATE: HOLD" in html.read_text(encoding="utf-8")
