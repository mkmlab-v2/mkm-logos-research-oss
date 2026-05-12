# @MKM12-METADATA
# Type: Logic
# Purpose: Multi-day frozen-prediction score rows for hit-rate sample depth.

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_VIX = _ROOT / "research" / "market_data" / "vix_daily_external_yf.csv"
_BUILD = _ROOT / "scripts" / "build_btrack_prophecy_score_from_ohlcv.py"
_EVAL = _ROOT / "scripts" / "eval_prophecy_hit_rate_v1.py"


def test_build_recent_trading_days_emits_n_rows(tmp_path) -> None:
    if not _VIX.is_file():
        return
    kcsv = tmp_path / "kospi_like.csv"
    shutil.copyfile(_VIX, kcsv)
    hypo = {
        "schema": "btrack_hypothesis_prophecy_v1",
        "prediction": {"instrument": "kospi", "direction": "bear"},
        "ts_utc": "2020-01-01T00:00:00Z",
    }
    hyp_path = tmp_path / "hyp.json"
    hyp_path.write_text(json.dumps(hypo), encoding="utf-8")
    out_score = tmp_path / "score.json"

    r = subprocess.run(
        [
            sys.executable,
            str(_BUILD),
            "--hypothesis-json",
            str(hyp_path),
            "--kospi-csv",
            str(kcsv),
            "--recent-trading-days",
            "12",
            "--output",
            str(out_score),
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert r.returncode == 0, r.stderr
    doc = json.loads(out_score.read_text(encoding="utf-8"))
    assert doc.get("schema") == "btrack_prophecy_score_v1"
    rows = doc.get("rows") or []
    assert len(rows) == 12
    assert doc.get("meta", {}).get("batch_eval_dates")
    ev = subprocess.run(
        [
            sys.executable,
            str(_EVAL),
            "--run-mode",
            "price",
            "--score-json",
            str(out_score),
            "--stdout-only",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert ev.returncode == 0, ev.stderr
    rep = json.loads(ev.stdout)
    assert rep.get("metrics", {}).get("n_evaluated") == 12


def test_force_dual_leg_cli_btc_hypothesis_emits_multi_inputs_and_dual_rows_per_date(tmp_path) -> None:
    if not _VIX.is_file():
        return
    kcsv = tmp_path / "kospi_like.csv"
    bcsv = tmp_path / "btc_like.csv"
    shutil.copyfile(_VIX, kcsv)
    shutil.copyfile(_VIX, bcsv)
    hypo = {
        "schema": "btrack_hypothesis_prophecy_v1",
        "boundary_ack": True,
        "ts_utc": "2020-01-01T00:00:00Z",
        "prediction": {"instrument": "btc", "direction": "bear"},
    }
    hyp_path = tmp_path / "hyp.json"
    hyp_path.write_text(json.dumps(hypo), encoding="utf-8")
    out_score = tmp_path / "score.json"

    r = subprocess.run(
        [
            sys.executable,
            str(_BUILD),
            "--hypothesis-json",
            str(hyp_path),
            "--kospi-csv",
            str(kcsv),
            "--btc-csv",
            str(bcsv),
            "--recent-trading-days",
            "2",
            "--force-dual-leg-panel",
            "--output",
            str(out_score),
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert r.returncode == 0, r.stderr
    doc = json.loads(out_score.read_text(encoding="utf-8"))
    inp = doc.get("inputs") or {}
    assert inp.get("hypothesis_instrument_declared") == "btc"
    assert inp.get("effective_instrument") == "multi"
    assert inp.get("force_dual_leg_panel") is True
    rows = doc.get("rows") or []
    assert len(rows) == 4
    by_date: dict[str, set[str]] = {}
    for row in rows:
        ed = row.get("eval_date")
        ins = row.get("instrument")
        assert ed and ins
        by_date.setdefault(ed, set()).add(ins)
    assert len(by_date) == 2
    assert all(legs == {"kospi", "btc"} for legs in by_date.values())
