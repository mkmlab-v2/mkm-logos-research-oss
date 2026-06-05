from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_q09_gold_chain_passes():
    cp = subprocess.run(
        [sys.executable, str(ROOT / "scripts/run_logos_gold_q09_kospi_report_chain_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=180,
    )
    assert cp.returncode == 0, cp.stderr or cp.stdout
    gold = json.loads((ROOT / "reports/logos_gold_query_eval_v1_latest.json").read_text(encoding="utf-8-sig"))
    q09 = next(r for r in gold["rows"] if r["id"] == "q09")
    assert q09["gate_pass"] is True
    assert (gold["summary"]["items_evaluated"]) >= 9
