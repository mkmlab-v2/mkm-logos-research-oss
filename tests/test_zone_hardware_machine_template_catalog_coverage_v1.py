from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "data/btrack_fixtures/zone_hardware_machine_log_samples_v1.jsonl"
CATALOG = ROOT / "codebook/templates/zone_hardware_machine_templates_prospect_v1.jsonl"
COVERAGE_RUNNER = ROOT / "scripts/run_zone_hardware_machine_template_catalog_coverage_v1.py"
TWIN_GATE = ROOT / "scripts/build_zone_hardware_machine_twin_gate_v1.py"
PIPELINE = ROOT / "scripts/run_zone_hardware_machine_prospect_pipeline_v1.py"


def test_coverage_fixture_full_match_on_prospect() -> None:
    from scripts.zone_hardware_machine_template_catalog_coverage_v1_lib import evaluate_corpus_coverage

    row = evaluate_corpus_coverage(
        FIXTURE,
        catalog_path=CATALOG,
        shard_path=ROOT / "codebook/shards/zone_hardware_machine.json",
    )
    assert row["snippet_candidates_total"] >= 9
    assert row["wire_match_rate"] == 1.0


def test_twin_gate_exact_restore_all_pass() -> None:
    from scripts.build_zone_hardware_machine_twin_gate_v1 import build_twin_gate_report

    report = build_twin_gate_report(
        catalog_path=CATALOG,
        manifest_path=ROOT / "codebook/templates/zone_hardware_machine_templates_manifest_v1.json",
    )
    assert report["twin_gate_exact_restore_all_pass"] is True
    assert report["gate_status"] == "pass"


def test_coverage_runner_smoke(tmp_path: Path) -> None:
    report = tmp_path / "coverage.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(COVERAGE_RUNNER),
            "--input-jsonl",
            str(FIXTURE),
            "--report-out",
            str(report),
            "--artifact-out",
            str(tmp_path / "art.json"),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(report.read_text(encoding="utf-8"))
    assert doc["schema"] == "zone_hardware_machine_template_catalog_coverage_v1"
    assert doc["aggregate"]["wire_match_rate"] == 1.0


def test_pipeline_smoke() -> None:
    proc = subprocess.run(
        [sys.executable, str(PIPELINE), "--skip-prospect-build"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
