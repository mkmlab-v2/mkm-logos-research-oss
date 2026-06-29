"""Tests for check_kstartup_startup_package_ai_paste_lint_v1.py"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from check_kstartup_startup_package_ai_paste_lint_v1 import lint_paste_dir  # noqa: E402


def test_lint_real_paste_dir_if_present():
    paste_dir = ROOT / "reports/kstartup_startup_package_ai_paste_ready"
    if not (paste_dir / "plan_01_summary_paste.txt").is_file():
        return
    report = lint_paste_dir(paste_dir)
    assert report["schema"] == "kstartup_startup_package_ai_paste_lint_v1"
    assert "files" in report


def test_lint_catches_duplicate_heading(tmp_path: Path):
    d = tmp_path / "paste"
    d.mkdir()
    body = "2.1 문제\n\n" + ("내용입니다. " * 40) + "\n\n2.1 문제\n\n또 나옵니다."
    for fname, min_c in [
        ("plan_01_summary_paste.txt", 120),
        ("plan_02_market_problem_paste.txt", 200),
        ("plan_03_tech_roadmap_paste.txt", 400),
        ("plan_04_growth_funding_paste.txt", 120),
        ("plan_05_team_paste.txt", 80),
        ("plan_06_ai_talent_2p_paste.txt", 200),
    ]:
        text = body if fname == "plan_02_market_problem_paste.txt" else ("x" * max(min_c, 150))
        (d / fname).write_text(text, encoding="utf-8")
    report = lint_paste_dir(d)
    assert report["ok"] is False
    assert any("duplicate_heading" in e for e in report["errors"])
