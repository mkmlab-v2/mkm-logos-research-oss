"""Universal Matrix lane wire AB — Golden 40 / active report isolation."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
ACTIVE = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"

LANES = (
    ("finance", "comp_universal_bench_matrix_wire_ab_finance_v1.json", 71),
    ("enterprise", "comp_universal_bench_matrix_wire_ab_enterprise_v1.json", 120),
    ("ijeoma", "comp_universal_bench_matrix_wire_ab_ijeoma_v1.json", 99),
    ("ijeoma_chunk", "comp_universal_bench_matrix_wire_ab_ijeoma_chunk_v1.json", 90),
)


def test_wire_ab_lane_artifacts_exist_and_isolate_golden():
    before_g = GOLDEN.read_text(encoding="utf-8")
    before_a = ACTIVE.read_text(encoding="utf-8")
    for lane_key, fname, expected_cases in LANES:
        out = ROOT / "reports/constitution/btrack_pilot" / fname
        assert out.is_file(), fname
        doc = json.loads(out.read_text(encoding="utf-8"))
        assert doc["case_count"] == expected_cases, lane_key
        assert doc["active_report_untouched"] is True
        assert "economy_baseline" in doc
        assert "economy_plus_wire_selective" in doc


def test_wire_ab_lane_script_dry_run():
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_universal_compression_bench_wire_ab_lane_v1.py",
            "--lane",
            "finance",
            "--dry-run",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr

