"""Regression for build_kospi_stress_observation_hypothesis_v1.py."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_kospi_stress_observation_hypothesis_v1.py"
SCHEMA_PATH = ROOT / "docs" / "final" / "schemas" / "kospi_stress_observation_hypothesis_v1.schema.json"


def _write_minimal_kospi(path: Path, *, volatile: bool) -> None:
    """10 rows of dates + Close; if volatile, last 5 days oscillate for high stdev."""
    rows = ["Date,Close"]
    base = 100.0
    start = date(2021, 6, 1)
    for i in range(10):
        d = (start + timedelta(days=i)).isoformat()
        if volatile and i >= 5:
            c = base * (1.05 if i % 2 == 0 else 0.96)
        else:
            c = base + i * 0.01
        rows.append(f"{d},{c}")
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def _write_flow(path: Path, foreign: float) -> None:
    path.write_text(
        "ym,foreign_net_buy,institution_net_buy,program_net_buy,usdkrw_change_pct,rates_front_end_change_bp\n"
        f"2026-04,{foreign},0,0,0,0\n",
        encoding="utf-8",
    )


def _run(tmp: Path, kospi: Path, flow: Path, out: Path, *, extra: list[str] | None = None) -> dict:
    cmd = [
        sys.executable,
        str(SCRIPT),
        "--kospi-csv",
        str(kospi),
        "--flow-csv",
        str(flow),
        "--output",
        str(out),
        "--vol-threshold",
        "0.05",
    ]
    if extra:
        cmd.extend(extra)
    subprocess.run(cmd, check=True, cwd=str(ROOT))
    return json.loads(out.read_text(encoding="utf-8"))


def test_schema_file_exists() -> None:
    assert SCHEMA_PATH.is_file()


def test_insufficient_rows_ok_false(tmp_path: Path) -> None:
    k = tmp_path / "k.csv"
    k.write_text("Date,Close\n2026-05-01,100\n", encoding="utf-8")
    f = tmp_path / "f.csv"
    _write_flow(f, 1.0)
    out = tmp_path / "out.json"
    doc = _run(tmp_path, k, f, out)
    assert doc.get("ok") is False
    assert doc["schema"] == "kospi_stress_observation_hypothesis_v1"


def test_vol_eased_and_composite_with_positive_flow(tmp_path: Path) -> None:
    k = tmp_path / "k.csv"
    _write_minimal_kospi(k, volatile=False)
    f = tmp_path / "f.csv"
    _write_flow(f, 100.0)
    out = tmp_path / "out.json"
    doc = _run(tmp_path, k, f, out)
    assert doc.get("ok") is True
    assert doc["gates"]["vol_stress_eased"] is True
    assert doc["gates"]["monthly_foreign_net_non_negative"] is True
    assert doc["composite_stress_ease_candidate"] is True
    assert "realized_vol_5d_logret_stdev" in doc["metrics"]


def test_vol_not_eased_when_oscillating(tmp_path: Path) -> None:
    k = tmp_path / "k.csv"
    _write_minimal_kospi(k, volatile=True)
    f = tmp_path / "f.csv"
    _write_flow(f, 100.0)
    out = tmp_path / "out.json"
    doc = _run(tmp_path, k, f, out, extra=["--vol-threshold", "0.001"])
    assert doc.get("ok") is True
    assert doc["gates"]["vol_stress_eased"] is False
    assert doc["composite_stress_ease_candidate"] is False


def test_jsonschema_optional(tmp_path: Path) -> None:
    pytest.importorskip("jsonschema")
    from jsonschema import Draft202012Validator

    k = tmp_path / "k.csv"
    _write_minimal_kospi(k, volatile=False)
    f = tmp_path / "f.csv"
    _write_flow(f, -500.0)
    out = tmp_path / "out.json"
    doc = _run(tmp_path, k, f, out)
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(doc)
    assert doc["composite_stress_ease_candidate"] is False
