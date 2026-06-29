"""Lens sovereignty report builder smoke."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_build_lens_sovereignty_report_from_disk_wf() -> None:
    wf = ROOT / "reports/kospi_lens_ablation_backtest_walkforward_latest.json"
    if not wf.is_file():
        return
    import subprocess
    import sys

    r = subprocess.run(
        [sys.executable, "scripts/build_lens_sovereignty_report_v1.py"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr
    out = ROOT / "docs/final/artifacts/lens_sovereignty_report_v1_latest.json"
    assert out.is_file()
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "lens_sovereignty_report_v1"
    assert doc["narrative_temporal_axis_verdict"] in ("KEEP", "MODIFY", "TRASH")
    assert doc["pack0b_rail"]["forbidden_in_market_verdict"] is True
    assert doc["promotion_ready"] is False


def test_build_lens_sovereignty_report_v1_1_from_disk() -> None:
    bp = ROOT / "docs/final/artifacts/lens_sovereignty_blueprint_v1_1.json"
    wf = ROOT / "reports/kospi_lens_ablation_backtest_walkforward_latest.json"
    if not bp.is_file() or not wf.is_file():
        return
    import subprocess
    import sys

    r = subprocess.run(
        [
            sys.executable,
            "scripts/build_lens_sovereignty_report_v1.py",
            "--blueprint",
            str(bp),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr
    out = ROOT / "docs/final/artifacts/lens_sovereignty_report_v1_1_latest.json"
    assert out.is_file()
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "lens_sovereignty_report_v1_1"
    assert doc["daily_kospi_wf"]["verdict"] in ("KEEP", "MODIFY", "TRASH")
    assert doc["role_contract_verdict"] in (
        "ROLE_ALIGNED",
        "ROLE_PARTIAL",
        "ROLE_FAIL",
        "ROLE_MISSING",
    )
    assert doc["promotion_ready"] is False


def test_build_lens_sovereignty_report_v1_2_from_disk() -> None:
    bp = ROOT / "docs/final/artifacts/lens_sovereignty_blueprint_v1_2.json"
    wf = ROOT / "reports/kospi_lens_ablation_backtest_walkforward_latest.json"
    if not bp.is_file() or not wf.is_file():
        return
    import subprocess
    import sys

    r = subprocess.run(
        [sys.executable, "scripts/build_lens_sovereignty_supplementary_rails_v1_2.py"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr
    r2 = subprocess.run(
        [
            sys.executable,
            "scripts/build_lens_sovereignty_report_v1.py",
            "--blueprint",
            str(bp),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r2.returncode == 0, r2.stderr
    out = ROOT / "docs/final/artifacts/lens_sovereignty_report_v1_2_latest.json"
    assert out.is_file()
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "lens_sovereignty_report_v1_2"
    assert "supplementary_rails_v1_2" in doc
    assert doc["supplementary_verdict"] in (
        "SUPP_ALIGNED",
        "SUPP_PARTIAL",
        "SUPP_FAIL",
        "SUPP_PENDING",
    )
    assert doc["promotion_ready"] is False
