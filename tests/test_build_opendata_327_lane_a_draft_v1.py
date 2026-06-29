from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts/build_opendata_327_lane_a_draft_v1.py"


def test_lane_a_draft_builder() -> None:
    proc = subprocess.run([sys.executable, str(SCRIPT)], cwd=str(ROOT), capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    out = ROOT / "reports/opendata_327_lane_a_draft_v1_latest.json"
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["completed_count"] == doc["total_llm_tasks"] == 8
    assert doc["pending_task_ids"] == []
    part_c = next(c for c in doc["completed"] if c["task_id"] == "327-narrative-part-c")
    assert "비용·품질 거버넌스" in part_c["output_markdown"]
    assert part_c["grep"]["ok"] is True
    assert "47%" not in part_c["output_markdown"]
    assert not re.search(r"Track\s+A", part_c["output_markdown"], re.I)
    assert "[DRAFT] block not found" not in part_c["output_markdown"]
