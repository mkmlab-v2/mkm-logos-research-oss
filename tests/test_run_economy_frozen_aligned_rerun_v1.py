from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "run_economy_frozen_aligned_rerun_v1.py"
LEXICON = (
    ROOT / "reports" / "constitution" / "btrack_pilot" / "master_codebook_lexicon_v1_41708_rows_latest.json"
)


def test_frozen_aligned_rerun_smoke(tmp_path: Path) -> None:
    if not LEXICON.is_file():
        return
    out_summary = tmp_path / "summary.json"
    out_report = tmp_path / "report.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--lexicon",
            str(LEXICON),
            "--out-summary",
            str(out_summary),
            "--out-report",
            str(out_report),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(out_summary.read_text(encoding="utf-8"))
    assert doc["schema"] == "economy_frozen_aligned_rerun_v1"
    assert doc["promote_active"] is False
    assert doc["per_case"]["unchanged_case_count"] + doc["per_case"]["changed_case_count"] == 40
