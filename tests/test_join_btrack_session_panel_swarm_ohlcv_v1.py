# -*- coding: utf-8 -*-
from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_JOIN = _ROOT / "scripts" / "join_btrack_session_panel_swarm_ohlcv_v1.py"
_ENRICH = _ROOT / "scripts" / "enrich_btrack_wide_sasang_proxy_v1.py"
_PANEL = _ROOT / "tests" / "fixtures" / "btrack_join_panel_smoke_v1.csv"
_SWARM = _ROOT / "tests" / "fixtures" / "btrack_swarm_smoke_v1.csv"
_OHLCV = _ROOT / "tests" / "fixtures" / "btrack_join_ohlcv_smoke_v1.csv"


def test_join_panel_swarm_ohlcv_smoke(tmp_path: Path) -> None:
    out_csv = tmp_path / "joined.csv"
    out_meta = tmp_path / "joined.meta.json"
    r = subprocess.run(
        [
            sys.executable,
            str(_JOIN),
            "--panel-csv",
            str(_PANEL),
            "--swarm-csv",
            str(_SWARM),
            "--swarm-date-col",
            "date",
            "--ohlcv-csv",
            str(_OHLCV),
            "--ohlcv-date-col",
            "Date",
            "--out-csv",
            str(out_csv),
            "--out-meta-json",
            str(out_meta),
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 0, r.stderr
    with out_csv.open(newline="", encoding="utf-8") as fp:
        rows = list(csv.DictReader(fp))
    assert len(rows) == 3
    assert rows[0]["swarm_panic_ratio"] == "0.2"
    assert rows[0]["ohlcv_close"] == "100"
    meta = json.loads(out_meta.read_text(encoding="utf-8"))
    assert meta.get("schema") == "btrack_session_panel_swarm_ohlcv_join_v1"
    assert meta.get("counts", {}).get("n_rows_with_any_swarm_cell_nonblank") == 3


def test_enrich_sasang_proxy_smoke(tmp_path: Path) -> None:
    wide = tmp_path / "wide.csv"
    wide.write_text(
        "session_local_date,swarm_panic_ratio,swarm_fomo_index,swarm_consensus_strength,ohlcv_close\n"
        "2024-06-12,0.2,0.3,0.7,100\n",
        encoding="utf-8",
    )
    out = tmp_path / "enriched.csv"
    r = subprocess.run(
        [
            sys.executable,
            str(_ENRICH),
            "--input-csv",
            str(wide),
            "--out-csv",
            str(out),
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 0, r.stderr
    with out.open(newline="", encoding="utf-8") as fp:
        row = next(csv.DictReader(fp))
    assert row["sasang_geumhwa_state"] == "0"
    assert float(row["sasang_geumhwa_score"]) == pytest.approx(0.235, abs=1e-3)


def test_build_swarm_csv_from_jsonl_smoke(tmp_path: Path) -> None:
    src = _ROOT / "tests" / "fixtures" / "btrack_swarm_smoke_v1.jsonl"
    out = tmp_path / "swarm.csv"
    r = subprocess.run(
        [
            sys.executable,
            str(_ROOT / "scripts" / "build_swarm_sentiment_daily_csv_from_jsonl_v1.py"),
            "--jsonl",
            str(src),
            "--out-csv",
            str(out),
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 0, r.stderr
    with out.open(newline="", encoding="utf-8") as fp:
        rows = list(csv.DictReader(fp))
    assert len(rows) == 3
    assert rows[0]["swarm_panic_ratio"] == "0.2"
