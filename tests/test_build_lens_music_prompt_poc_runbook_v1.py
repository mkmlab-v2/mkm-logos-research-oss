from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_build_prompt_poc_runbook_watch(tmp_path):
    poc = tmp_path / "poc.json"
    poc.write_text(
        json.dumps(
            {
                "schema": "lens_music_prompt_poc_metric_v1",
                "result": {"state": "WATCH", "passed": False},
                "kpi": {"style_delta_rate": 0.1, "overlay_style_match_rate": 0.5},
                "targets": {"style_delta_rate_min": 0.3, "overlay_style_match_rate_min": 0.67},
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    out = tmp_path / "runbook.json"
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/build_lens_music_prompt_poc_runbook_v1.py"),
            "--poc-json",
            str(poc),
            "--out",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "lens_music_prompt_poc_runbook_v1"
    assert doc["state"] == "WATCH"
    assert len(doc["recommendations"]) >= 1
