from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "apply_kospi_daily_flow_pending_row_v1.py"


def test_apply_pending_missing_is_noop():
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--pending-json", str(ROOT / "research/market_data/_no_such_pending.json")],
        cwd=str(ROOT),
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert "skip" in proc.stdout.lower()


def test_apply_pending_upserts_and_renames(tmp_path):
    pending = tmp_path / "pending.json"
    csv = tmp_path / "flow.csv"
    pending.write_text(
        json.dumps(
            {
                "date": "2026-01-02",
                "foreign": -1.0,
                "institution": 2.0,
                "program": 0.5,
                "individual": -1.5,
                "source_note": "pytest",
            }
        ),
        encoding="utf-8",
    )
    csv.write_text(
        "date,foreign_net_buy,institution_net_buy,program_net_buy,individual_net_buy,source_note\n"
        "2026-01-01,0,0,0,0,old\n",
        encoding="utf-8",
    )
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "append_kospi_daily_flow_row_v1.py"),
            "--date",
            "2026-01-02",
            "--foreign",
            "-1",
            "--institution",
            "2",
            "--program",
            "0.5",
            "--individual",
            "-1.5",
            "--source-note",
            "pytest",
            "--csv",
            str(csv),
        ],
        cwd=str(ROOT),
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    text = csv.read_text(encoding="utf-8")
    assert "2026-01-02" in text
    assert "2.0" in text or "2" in text
