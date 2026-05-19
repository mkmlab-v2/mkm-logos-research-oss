"""generate_marketing_channel_draft_v1 — youtube / newsletter assemble-only."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/generate_marketing_channel_draft_v1.py"
EXAMPLE = ROOT / "data/marketing/marketing_content_queue_v1.example.json"


def test_youtube_draft_from_example(tmp_path):
    q = tmp_path / "q.json"
    doc = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    for it in doc["items"]:
        if it.get("channel") == "youtube_script":
            it["status"] = "pending"
    q.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--queue", str(q), "--channel", "youtube_script"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    out_dir = ROOT / "reports/marketing/youtube_scripts"
    assert any(p.name.endswith("_[DRAFT].md") for p in out_dir.iterdir() if p.is_file())
    updated = json.loads(q.read_text(encoding="utf-8"))
    yt = next(i for i in updated["items"] if i["id"] == "compression_discipline_youtube_q2")
    assert yt["status"] == "drafted"
