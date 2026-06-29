"""Smoke: archive limitless trilogy report builder."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "experiments/no_guard_limit_test/results"


def test_archive_builder_strict_schema() -> None:
    from scripts.sandbox.build_archive_limitless_trilogy_report_v1 import build_report

    doc = build_report(strict=False)
    assert doc.get("schema") == "archive_limitless_trilogy_report_v1"
    assert doc.get("archive_status") == "frozen_b_track"
    assert doc.get("case_count") == 20
    assert len(doc.get("trilogy_table") or []) == 3
    forbidden = doc.get("forbidden_claims") or []
    assert "track_a_promotion" in forbidden
    assert "corpus_bloat_default_path" in forbidden


def test_archive_cli_writes_json() -> None:
    out = RESULTS / "archive_limitless_trilogy_report_test.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/sandbox/build_archive_limitless_trilogy_report_v1.py"),
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
    assert doc.get("ssot_one_liner_ko")
    assert doc.get("evidence_paths")


def test_phase2_bench_cli_dry_run() -> None:
    for script, out_name in (
        ("run_prism_dynamic_pinset_heavy_bench_v1.py", "prism_dynamic_pinset_heavy_bench_test.json"),
        ("run_prism_no_guard_meta_corpus_bench_v1.py", "prism_no_guard_meta_corpus_bench_test.json"),
    ):
        out = RESULTS / out_name
        proc = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/sandbox" / script),
                "--dry-run",
                "--out-json",
                str(out),
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == 0, proc.stderr
