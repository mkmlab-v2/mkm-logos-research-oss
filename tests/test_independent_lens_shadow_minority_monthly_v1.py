# @MKM12-METADATA
# Type: Logic
# Purpose: Regression for shadow history minority monthly rollup v1.
# Keywords: shadow_gate, minority_lens, rollup

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_RUNNER = _ROOT / "scripts/report_independent_lens_shadow_minority_monthly_v1.py"
_FIXTURE = _ROOT / "tests/fixtures/independent_lens_shadow_history_minority_sample.jsonl"


def test_runner_emits_monthly_rollup(tmp_path: Path) -> None:
    out = tmp_path / "rollup.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(_RUNNER),
            "--history-jsonl",
            str(_FIXTURE),
            "--output",
            str(out),
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "independent_lens_shadow_minority_monthly_v1"
    assert doc.get("history_rows_total") == 4
    assert doc.get("rows_with_minority_lens_total") == 3
    by_m = doc.get("by_month") or {}
    m5 = by_m.get("2026-05") or {}
    assert m5.get("total_rows") == 3
    assert m5.get("rows_with_minority_lens") == 2
    assert m5.get("minority_lens_counts") == {"logos": 2}
    assert m5.get("distinct_narrative_digest_count") == 2
    m6 = by_m.get("2026-06") or {}
    assert m6.get("minority_lens_counts") == {"myeongni": 1}
