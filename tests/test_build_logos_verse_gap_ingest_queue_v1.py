"""Gap ingest queue exporter."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/build_logos_verse_gap_ingest_queue_v1.py"
META = ROOT / "docs/final/artifacts/logos_verse_gap_ingest_queue_v1_latest.json"


def test_gap_queue_export_smoke():
    rc = subprocess.run([sys.executable, str(SCRIPT)], cwd=str(ROOT), capture_output=True, text=True)
    assert rc.returncode == 0, rc.stderr
    assert META.is_file()
    meta = json.loads(META.read_text(encoding="utf-8"))
    assert meta.get("rows_written") == meta.get("gap_count_expected")
    assert meta.get("rows_written", 0) > 2000
