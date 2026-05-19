"""Gemini per-date panel: causal context, dry-run, harness wiring."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_causal_context_uses_only_past_dates() -> None:
    btc = ROOT / "research/market_data/btc_daily_external_yf.csv"
    if not btc.is_file():
        pytest.skip("btc csv missing")
    from scripts.btrack_gemini_per_date_core_v1 import build_causal_context_for_eval_date

    from scripts.btrack_gemini_per_date_core_v1 import resolve_eval_dates

    dates = resolve_eval_dates(recent_trading_days=5, kospi_csv=ROOT / "research/market_data/kospi_daily_external_yf.csv", btc_csv=btc)
    if not dates:
        pytest.skip("no eval dates")
    ed = dates[-1]
    ctx = build_causal_context_for_eval_date(eval_date=ed, btc_csv=btc)
    for r in ctx.get("causal_price_daily_returns") or []:
        assert str(r.get("eval_date") or "")[:10] < ed


def test_build_gemini_per_date_dry_run() -> None:
    out = ROOT / "reports" / "_tmp_gemini_per_date_dry.json"
    r = subprocess.run(
        [
            sys.executable,
            "scripts/build_btrack_gemini_per_date_directions_v1.py",
            "--dry-run",
            "--recent-trading-days",
            "5",
            "--output",
            str(out),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "btrack_gemini_per_date_directions_v1"
    assert doc["dry_run"] is True
    assert doc["hypothesis_tier"] == "B"
    assert len(doc.get("plan", {}).get("eval_dates") or []) == 5
    out.unlink(missing_ok=True)


def test_harness_dry_run_includes_gemini_per_date_plan() -> None:
    out = ROOT / "reports" / "_tmp_harness_gemini_pd_dry.json"
    r = subprocess.run(
        [
            sys.executable,
            "scripts/run_btrack_model_swap_harness_v1.py",
            "--dry-run",
            "--include-gemini-per-date",
            "--output",
            str(out),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert "gemini_per_date_30d" in doc["plan"]["engines"]
    out.unlink(missing_ok=True)
