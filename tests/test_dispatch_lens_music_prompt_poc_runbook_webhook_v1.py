from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_dispatch_poc_runbook_skips_when_webhook_not_configured(tmp_path):
    hist = tmp_path / "hist.jsonl"
    runbook = tmp_path / "runbook.json"
    runbook.write_text(
        json.dumps(
            {
                "schema": "lens_music_prompt_poc_runbook_v1",
                "state": "WATCH",
                "recommendations": [{"cause": "style_delta_below_target", "priority": "high"}],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    out = tmp_path / "dispatch.json"
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/dispatch_lens_music_prompt_poc_runbook_webhook_v1.py"),
            "--runbook-json",
            str(runbook),
            "--output-json",
            str(out),
            "--webhook-env",
            "MISSING_TEST_WEBHOOK",
            "--require-watch",
            "--require-high-priority",
            "--history-jsonl",
            str(hist),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "lens_music_prompt_poc_runbook_webhook_dispatch_v1"
    assert doc["decision"]["watch_gate_passed"] is True
    assert doc["decision"]["high_priority_gate_passed"] is True
    assert doc["dispatch"]["status"] == "skipped"
    assert doc["dispatch"]["reason"] == "webhook_not_configured"
    lines = [ln.strip() for ln in hist.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row["schema"] == "lens_music_prompt_poc_runbook_webhook_history_row_v1"
    assert row["dispatch_status"] == "skipped"
    assert row["skip_reason"] == "webhook_not_configured"
