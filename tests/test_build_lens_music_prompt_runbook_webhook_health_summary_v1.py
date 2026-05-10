from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "lens_music_prompt_runbook_webhook_history_sample_v1.jsonl"


def test_health_summary_aggregates_fixture(tmp_path):
    out = tmp_path / "health.json"
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/build_lens_music_prompt_runbook_webhook_health_summary_v1.py"),
            "--history-jsonl",
            str(FIXTURE),
            "--max-rows",
            "100",
            "--out",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "lens_music_prompt_runbook_webhook_health_v1"
    assert doc["samples_in_window"] == 3
    assert doc["counts"]["sent"] == 1
    assert doc["counts"]["skipped"] == 2
    assert doc["counts"]["failed"] == 0
    reasons = doc["skip_reason_top"]
    assert reasons[0]["reason"] == "webhook_not_configured"
    assert reasons[0]["count"] == 2
    assert doc["rates"]["skipped_rate"] > 0
