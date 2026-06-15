"""zone_f_code template catalog coverage eval."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "data/compression/fixtures/zone_f_code_corpus_extract_fixture_v1.jsonl"
CONTRIB = ROOT / "data/compression/contributions/open_bench_coding_snippet_seed_v1.jsonl"
CATALOG = ROOT / "codebook/templates/zone_f_code_templates_v1.jsonl"
COVERAGE_RUNNER = ROOT / "scripts/run_zone_f_code_template_catalog_coverage_v1.py"
PIPELINE = ROOT / "scripts/run_zone_f_code_template_catalog_pipeline_v1.py"


def test_coverage_open_bench_coding_seed_full_match() -> None:
    from scripts.zone_f_code_template_catalog_coverage_v1_lib import evaluate_corpus_coverage

    row = evaluate_corpus_coverage(
        CONTRIB,
        catalog_path=CATALOG,
        shard_path=ROOT / "codebook/shards/zone_f_code.json",
    )
    assert row["snippet_candidates_total"] == 3
    assert row["wire_match_count"] == 3
    assert row["wire_match_rate"] == 1.0


def test_coverage_fixture_mixed_match() -> None:
    from scripts.zone_f_code_template_catalog_coverage_v1_lib import evaluate_corpus_coverage

    row = evaluate_corpus_coverage(
        FIXTURE,
        catalog_path=CATALOG,
        shard_path=ROOT / "codebook/shards/zone_f_code.json",
    )
    assert row["snippet_candidates_total"] == 4
    assert row["wire_match_count"] == 4
    assert row["wire_match_rate"] == 1.0


def test_coverage_runner_smoke(tmp_path: Path) -> None:
    report = tmp_path / "coverage.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(COVERAGE_RUNNER),
            "--input-jsonl",
            str(CONTRIB),
            "--report-out",
            str(report),
            "--artifact-out",
            str(tmp_path / "art.json"),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(report.read_text(encoding="utf-8"))
    assert doc["schema"] == "zone_f_code_template_catalog_coverage_v1"
    assert doc["aggregate"]["wire_match_rate"] == 1.0


def test_pipeline_dry_run_smoke() -> None:
    proc = subprocess.run(
        [sys.executable, str(PIPELINE)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
