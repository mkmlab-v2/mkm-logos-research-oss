"""Regression for build_kospi_july_scenario_band_tracker_v1.py."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_kospi_july_scenario_band_tracker_v1.py"
SCHEMA_PATH = ROOT / "docs" / "final" / "schemas" / "kospi_july_scenario_band_tracker_v1.schema.json"
PROPHECY = ROOT / "docs" / "final" / "artifacts" / "prophecy_2026_monthly_kospi_btc_fact_safe_v1.json"


def _write_flow(path: Path) -> None:
    path.write_text(
        "date,foreign_net_buy,institution_net_buy,program_net_buy,individual_net_buy,pension_proxy_net_buy,source_note\n"
        "2026-06-20,1000,500,0,800,-500,test\n"
        "2026-06-23,-42000,-10000,0,50000,-3000,test\n"
        "2026-06-24,2000,1000,0,3000,-800,test\n"
        "2026-06-25,3000,1500,0,4000,-600,test\n",
        encoding="utf-8",
    )


def _write_kospi(path: Path) -> None:
    path.write_text(
        "Date,Open,High,Low,Close,Volume\n"
        "2026-06-24,8500,8600,8400,8550,100\n"
        "2026-06-25,8550,9200,8500,9100,100\n",
        encoding="utf-8",
    )


def _run(tmp: Path, flow: Path, kospi: Path, out_json: Path, out_md: Path) -> dict:
    cmd = [
        sys.executable,
        str(SCRIPT),
        "--flow-csv",
        str(flow),
        "--kospi-csv",
        str(kospi),
        "--prophecy-json",
        str(PROPHECY),
        "--shock-json",
        str(tmp / "missing_shock.json"),
        "--output-json",
        str(out_json),
        "--output-md",
        str(out_md),
        "--pension-5d-sell-threshold",
        "-5000",
    ]
    subprocess.run(cmd, check=True, cwd=str(ROOT))
    return json.loads(out_json.read_text(encoding="utf-8"))


def test_schema_exists() -> None:
    assert SCHEMA_PATH.is_file()


def test_foreign_buy_streak_nudges_bull(tmp_path: Path) -> None:
    flow = tmp_path / "flow.csv"
    _write_flow(flow)
    kospi = tmp_path / "k.csv"
    _write_kospi(kospi)
    out_json = tmp_path / "out.json"
    out_md = tmp_path / "out.md"
    doc = _run(tmp_path, flow, kospi, out_json, out_md)
    assert doc["schema"] == "kospi_july_scenario_band_tracker_v1"
    assert doc["ok"] is True
    assert doc["send_gate"] == "HOLD"
    assert doc["axes"]["program"]["status"] == "GAP"
    adj = doc["scenario_weights"]["adjusted"]
    base = doc["scenario_weights"]["base"]
    assert adj["bull_pct"] >= base["bull_pct"]
    assert out_md.is_file()


def test_jsonschema_optional(tmp_path: Path) -> None:
    pytest.importorskip("jsonschema")
    from jsonschema import Draft202012Validator

    flow = tmp_path / "flow.csv"
    _write_flow(flow)
    kospi = tmp_path / "k.csv"
    _write_kospi(kospi)
    out_json = tmp_path / "out.json"
    out_md = tmp_path / "out.md"
    doc = _run(tmp_path, flow, kospi, out_json, out_md)
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(doc)
