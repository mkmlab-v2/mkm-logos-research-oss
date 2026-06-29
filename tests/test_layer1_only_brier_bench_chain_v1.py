from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COHORT = ROOT / "docs" / "final" / "artifacts" / "layer1_only_brier_bench_poc_v1_latest.json"
MAP = ROOT / "docs" / "final" / "artifacts" / "layer1_only_brier_bench_poc_registry_map_v1.json"
SEED = ROOT / "tests" / "fixtures" / "general_prophecy_registry_seed_5_v1.json"
REGISTER = ROOT / "scripts" / "register_layer1_only_brier_bench_poc_v1.py"
PROBE = ROOT / "scripts" / "probe_layer1_only_brier_bench_resolvers_v1.py"
CHAIN = ROOT / "scripts" / "run_layer1_only_brier_bench_chain_v1.py"


def test_register_dry_run_inserts_two_new_questions(tmp_path: Path) -> None:
    reg = tmp_path / "registry.json"
    reg.write_text(SEED.read_text(encoding="utf-8"), encoding="utf-8")
    out = tmp_path / "register_report.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(REGISTER),
            "--registry",
            str(reg),
            "--output-report",
            str(out),
            "--dry-run",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    report = json.loads(out.read_text(encoding="utf-8"))
    actions = report["actions"]
    assert any(a["action"] == "insert_question" for a in actions)
    assert any(a["question_id"] == "poc.us_unemployment_below_4pct_2026h2" for a in actions)


def test_probe_dry_run_holdout_safe(tmp_path: Path) -> None:
    out = tmp_path / "probe.json"
    proc = subprocess.run(
        [sys.executable, str(PROBE), "--output", str(out)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["resolved_candidate_count"] == 0
    assert all(p["status"] in ("dry_run", "holdout_pending") for p in report["probes"])


def test_chain_dry_run_exit_zero(tmp_path: Path) -> None:
    reg = tmp_path / "registry.json"
    reg.write_text(SEED.read_text(encoding="utf-8"), encoding="utf-8")
    # Chain uses default registry path — run with skip-register for isolation
    proc = subprocess.run(
        [sys.executable, str(CHAIN), "--dry-run", "--skip-register"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr


def test_cohort_map_covers_all_forecasts() -> None:
    cohort = json.loads(COHORT.read_text(encoding="utf-8"))
    mapping = json.loads(MAP.read_text(encoding="utf-8"))
    mapped = {m["poc_question_id"] for m in mapping["mappings"]}
    forecast_ids = {f["question_id"] for f in cohort["forecasts"]}
    assert forecast_ids == mapped
