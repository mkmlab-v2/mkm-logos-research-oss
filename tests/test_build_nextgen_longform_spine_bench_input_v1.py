"""Domain filter for B2B longform spine bench input."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts/build_nextgen_longform_spine_bench_input_v1.py"
MATRIX = ROOT / "docs/final/artifacts/UNIVERSAL_COMPRESSION_BENCH_MATRIX_INPUT_V1.json"


def test_domain_tag_filter_finance_macro_b2b(tmp_path: Path) -> None:
    out = tmp_path / "b2b_slice.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--matrix-input",
            str(MATRIX),
            "--out-json",
            str(out),
            "--domain-tag",
            "finance_macro_b2b",
            "--min-raw-bytes",
            "1",
            "--max-cases",
            "5",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["filter"]["domain_tag"] == "finance_macro_b2b"
    assert doc["case_count"] >= 1
    for c in doc["compression_cases"]:
        assert c.get("domain") == "finance_macro_b2b"
