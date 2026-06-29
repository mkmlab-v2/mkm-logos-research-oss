"""RQ-026 commander signoff + matrix coupling smoke."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_record_rq026_signoff_schema() -> None:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/record_rq026_commander_btrack_signoff_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    out = ROOT / "docs/final/artifacts/rq026_commander_btrack_signoff_v1_latest.json"
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "rq026_commander_btrack_signoff_v1"
    assert doc.get("approved", {}).get("rq026_btrack_continue") is True
    hold = doc.get("explicit_hold") or {}
    assert hold.get("ng40_codec_merge") is False
    assert hold.get("track_a_live_trading_auto_merge") is False


def test_sim_matrix_coupled_flag(tmp_path: Path) -> None:
    market = ROOT / "reports/btrack_per_date_directions_market_psych_v2.json"
    if not market.is_file():
        return
    out = tmp_path / "sim.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_sasang_temperament_agents_sim_stub_v1.py"),
            "--input",
            str(market),
            "--out",
            str(out),
            "--max-days",
            "5",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("inputs", {}).get("pathology_matrix_coupled") is True
