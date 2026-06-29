"""Smoke tests for KOSPI June evening miss insight chain (offline)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_calendar_miss_decomposition_from_eval() -> None:
    from scripts.build_kospi_june2026_calendar_miss_decomposition_v1 import build_miss_decomposition

    eval_path = ROOT / "reports/kospi_june2026_daily_prophecy_eval_latest.json"
    if not eval_path.is_file():
        return
    doc = build_miss_decomposition(json.loads(eval_path.read_text(encoding="utf-8")), eval_path=eval_path)
    assert doc["schema"] == "kospi_june2026_calendar_miss_decomposition_v1"
    assert doc["miss_day_count"] >= 1
    assert all(m.get("kospi_pred") for m in doc["miss_days"])


def test_daily_miss_insight_2026_06_26() -> None:
    from scripts.build_kospi_june2026_daily_miss_insight_v1 import build_daily_miss_insight

    cal = ROOT / "reports/kospi_202606_daily_prophecy_calendar_v1.json"
    ev = ROOT / "reports/kospi_june2026_daily_prophecy_eval_latest.json"
    ai = ROOT / "reports/kospi_june2026_4ai_prophecy_report_latest.json"
    if not (cal.is_file() and ev.is_file() and ai.is_file()):
        return
    doc = build_daily_miss_insight(
        session_date="2026-06-26",
        calendar=json.loads(cal.read_text(encoding="utf-8-sig")),
        eval_doc=json.loads(ev.read_text(encoding="utf-8-sig")),
        four_ai=json.loads(ai.read_text(encoding="utf-8-sig")),
    )
    assert doc is not None
    assert doc["outcome"] == "FAIL"
    assert doc["score"]["band_hit"] is True
    assert doc["structured_lessons"]


def test_evening_miss_insight_chain_smoke_skip_llm() -> None:
    ev = ROOT / "reports/kospi_june2026_daily_prophecy_eval_latest.json"
    if not ev.is_file():
        return
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_kospi_june2026_evening_miss_insight_chain_v1.py"),
            "--as-of-kst",
            "2026-06-26",
            "--skip-llm",
            "--report",
            "reports/_test_kospi_evening_miss_insight_chain_v1.json",
            "--insight-out",
            "reports/_test_kospi_daily_miss_insight_v1.json",
            "--miss-decomp-out",
            "reports/_test_kospi_calendar_miss_decomp_v1.json",
            "--miss-probe-out",
            "reports/_test_kospi_calendar_miss_flow_probe_v1.json",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    rep = json.loads((ROOT / "reports/_test_kospi_evening_miss_insight_chain_v1.json").read_text(encoding="utf-8"))
    assert rep["triggered"] is True
    assert rep["trigger_reason"] == "FAIL"
    insight = json.loads((ROOT / "reports/_test_kospi_daily_miss_insight_v1.json").read_text(encoding="utf-8"))
    assert insight["session_date"] == "2026-06-26"
