from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_dispatch_skips_when_webhook_not_configured(tmp_path):
    status = tmp_path / "status.json"
    status.write_text(
        json.dumps(
            {
                "schema": "lens_music_audition_governance_status_v1",
                "generated_at_utc": "2026-05-11T00:00:00Z",
                "state": "WATCH",
                "warn_ratio": 0.4,
                "warn_ratio_threshold": 0.2,
                "warn_count": 2,
                "sample_count": 5,
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
            str(ROOT / "scripts/dispatch_lens_music_audition_governance_webhook_v1.py"),
            "--status-json",
            str(status),
            "--output-json",
            str(out),
            "--webhook-env",
            "MISSING_TEST_WEBHOOK",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "lens_music_audition_governance_webhook_dispatch_v1"
    assert doc["dispatch"]["status"] == "skipped"
    assert doc["dispatch"]["reason"] == "webhook_not_configured"
