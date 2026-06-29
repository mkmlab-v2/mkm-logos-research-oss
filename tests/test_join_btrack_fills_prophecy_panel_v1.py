# -*- coding: utf-8 -*-
from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_JOIN = _ROOT / "scripts" / "join_btrack_fills_prophecy_panel_v1.py"
_FILLS = _ROOT / "tests" / "fixtures" / "btrack_fills_join_smoke_v1.json"
_PRP = _ROOT / "tests" / "fixtures" / "btrack_prophecy_per_date_join_smoke_v1.json"


def test_join_fills_prophecy_union_smoke(tmp_path: Path) -> None:
    out_csv = tmp_path / "joined.csv"
    out_meta = tmp_path / "joined.meta.json"
    r = subprocess.run(
        [
            sys.executable,
            str(_JOIN),
            "--fills-cache",
            str(_FILLS),
            "--per-date-json",
            str(_PRP),
            "--eval-lane-json",
            str(tmp_path / "missing_eval.json"),
            "--spine",
            "union",
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
    by_date = {row["utc_date"]: row for row in rows}
    assert by_date["2026-01-10"]["has_fills"] == "1"
    assert by_date["2026-01-10"]["has_prophecy"] == "1"
    assert by_date["2026-01-10"]["prp_predicted_direction"] == "bull"
    assert by_date["2026-01-10"]["fill_fill_count"] == "2"
    assert by_date["2026-01-11"]["has_fills"] == "1"
    assert by_date["2026-01-11"]["has_prophecy"] == "0"
    assert by_date["2026-01-12"]["has_fills"] == "0"
    assert by_date["2026-01-12"]["has_prophecy"] == "1"
    meta = json.loads(out_meta.read_text(encoding="utf-8"))
    assert meta.get("schema") == "btrack_fills_prophecy_join_v1"
    assert meta.get("research_only") is True
    assert meta.get("counts", {}).get("n_overlap_days") == 1

    overlap_csv = tmp_path / "overlap.csv"
    r2 = subprocess.run(
        [
            sys.executable,
            str(_JOIN),
            "--fills-cache",
            str(_FILLS),
            "--per-date-json",
            str(_PRP),
            "--out-csv",
            str(tmp_path / "wide2.csv"),
            "--out-overlap-csv",
            str(overlap_csv),
            "--out-meta-json",
            str(tmp_path / "m2.json"),
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r2.returncode == 0, r2.stderr
    with overlap_csv.open(newline="", encoding="utf-8") as fp:
        overlap = list(csv.DictReader(fp))
    assert len(overlap) == 1
    assert overlap[0]["utc_date"] == "2026-01-10"


def test_join_fills_prophecy_overlap_correlate_smoke(tmp_path: Path) -> None:
    overlap_csv = tmp_path / "overlap.csv"
    r0 = subprocess.run(
        [
            sys.executable,
            str(_JOIN),
            "--fills-cache",
            str(_FILLS),
            "--per-date-json",
            str(_PRP),
            "--out-csv",
            str(tmp_path / "wide.csv"),
            "--out-overlap-csv",
            str(overlap_csv),
            "--out-meta-json",
            str(tmp_path / "meta.json"),
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r0.returncode == 0, r0.stderr
    corr = _ROOT / "scripts" / "correlate_btrack_joined_wide_csv_v1.py"
    r1 = subprocess.run(
        [
            sys.executable,
            str(corr),
            "--input-csv",
            str(overlap_csv),
            "--y-col",
            "fill_realized_pnl_sum",
            "--x-auto-prefixes",
            "prp_",
            "--min-pairs",
            "1",
            "--stdout-only",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r1.returncode == 0, r1.stderr
    doc = json.loads(r1.stdout)
    assert doc.get("schema") == "btrack_joined_wide_correlation_v1"


def test_join_fills_spine_only(tmp_path: Path) -> None:
    out_csv = tmp_path / "fills_only.csv"
    r = subprocess.run(
        [
            sys.executable,
            str(_JOIN),
            "--fills-cache",
            str(_FILLS),
            "--per-date-json",
            str(_PRP),
            "--spine",
            "fills",
            "--out-csv",
            str(out_csv),
            "--out-meta-json",
            str(tmp_path / "m.json"),
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 0, r.stderr
    with out_csv.open(newline="", encoding="utf-8") as fp:
        rows = list(csv.DictReader(fp))
    assert len(rows) == 2
    assert {row["utc_date"] for row in rows} == {"2026-01-10", "2026-01-11"}
