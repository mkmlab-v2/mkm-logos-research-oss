"""push_marketing_draft_to_buffer_v1 — dry-run only (no API)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/push_marketing_draft_to_buffer_v1.py"


def test_dry_run_requires_human_approved(tmp_path):
    q = tmp_path / "q.json"
    doc = {
        "schema": "marketing_content_queue_v1",
        "items": [
            {
                "id": "compression_governance_moat_w12",
                "channel": "linkedin",
                "status": "drafted",
                "topic": "t",
                "locale": "en",
                "draft_paths": {"markdown": "reports/marketing/linkedin_drafts/x.md"},
            }
        ],
    }
    q.write_text(json.dumps(doc), encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--item-id", "compression_governance_moat_w12", "--queue", str(q)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 2
