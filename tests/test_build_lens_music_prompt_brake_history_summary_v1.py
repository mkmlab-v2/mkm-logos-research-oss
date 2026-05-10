from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_build_prompt_brake_history_summary(tmp_path):
    log = tmp_path / "hist.jsonl"
    rows = [
        {
            "schema": "lens_music_prompt_overlay_history_row_v1",
            "auto_brake_active": True,
            "trigger_governance_watch": True,
            "trigger_smoke_eval_watch": False,
            "answer_style": "calm_guarded",
        },
        {
            "schema": "lens_music_prompt_overlay_history_row_v1",
            "auto_brake_active": False,
            "trigger_governance_watch": False,
            "trigger_smoke_eval_watch": False,
            "answer_style": "bright_concise",
        },
    ]
    log.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    out = tmp_path / "summary.json"
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/build_lens_music_prompt_brake_history_summary_v1.py"),
            "--history-log-jsonl",
            str(log),
            "--out",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "lens_music_prompt_brake_history_summary_v1"
    assert doc["rows_scanned"] == 2
    assert doc["auto_brake_active_count"] == 1
    assert doc["trigger_counts"]["governance_watch"] == 1
