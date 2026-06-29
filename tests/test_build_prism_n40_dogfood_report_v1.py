"""Smoke: n40 dogfood extension report."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "experiments/no_guard_limit_test/results"


def test_n40_report_builder_dry_schema() -> None:
    from scripts.sandbox.build_prism_n40_dogfood_report_v1 import build_report

    doc = build_report(strict=False)
    assert doc.get("schema") == "prism_n40_dogfood_extension_v1"
    assert doc.get("case_count") == 40


def test_n40_report_strict_after_benches() -> None:
    out = RESULTS / "prism_n40_dogfood_extension_test.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/sandbox/build_prism_n40_dogfood_report_v1.py"),
            "--strict",
            "--out-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("complete") is True
    assert doc.get("summary", {}).get("wire_poc_pass") is True
