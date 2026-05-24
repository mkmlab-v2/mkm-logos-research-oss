"""Smoke: build_magic_orb_open_beta_traffic_summary_v1 aggregates probe history."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts" / "build_magic_orb_open_beta_traffic_summary_v1.py"


def test_summary_from_fixture_history(tmp_path: Path) -> None:
    hist = tmp_path / "history.jsonl"
    rows = [
        {
            "checked_at_utc": "2026-05-21T10:00:00Z",
            "all_ok": True,
            "results": [{"id": "mkmlife_oracle", "status": 200, "ok": True}],
        },
        {
            "checked_at_utc": "2026-05-21T11:00:00Z",
            "all_ok": False,
            "results": [{"id": "mkmlife_oracle", "status": 500, "ok": False}],
        },
    ]
    hist.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    out = tmp_path / "summary.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(BUILDER),
            "--history-jsonl",
            str(hist),
            "--output-json",
            str(out),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "magic_orb_open_beta_traffic_summary_v1"
    assert doc["history_entries_total"] == 2
    assert doc["urls"]["mkmlife_oracle"]["checks"] == 2
    assert doc["streak_all_ok_from_latest"] == 0
