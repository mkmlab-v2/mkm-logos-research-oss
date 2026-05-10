from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_build_prompt_brake_trend(tmp_path):
    hist = tmp_path / "hist.jsonl"
    rows = [
        {
            "ts_utc": "2026-05-10T10:00:00Z",
            "auto_brake_active": True,
            "trigger_governance_watch": True,
            "trigger_smoke_eval_watch": False,
        },
        {
            "ts_utc": "2026-05-10T10:10:00Z",
            "auto_brake_active": False,
            "trigger_governance_watch": False,
            "trigger_smoke_eval_watch": False,
        },
        {
            "ts_utc": "2026-05-11T11:00:00Z",
            "auto_brake_active": True,
            "trigger_governance_watch": False,
            "trigger_smoke_eval_watch": True,
        },
    ]
    hist.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    out = tmp_path / "trend.json"
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/build_lens_music_prompt_brake_trend_v1.py"),
            "--history-log-jsonl",
            str(hist),
            "--out",
            str(out),
            "--active-rate-watch-threshold",
            "0.4",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "lens_music_prompt_brake_trend_v1"
    assert doc["rows_scanned"] == 3
    assert doc["auto_brake_active_count"] == 2
    assert doc["state"] == "WATCH"
    assert len(doc["daily_series"]) >= 2
