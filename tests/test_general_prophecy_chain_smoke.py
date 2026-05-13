# @MKM12-METADATA
# Type: Logic
# Purpose: Smoke subprocess for general prophecy CLI (no network).

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]


def test_generate_general_prophecy_dry_run_with_official_seed_merge() -> None:
    r = subprocess.run(
        [
            sys.executable,
            str(_ROOT / "scripts" / "generate_general_prophecy_v1.py"),
            "--dry-run",
            "--merge-from",
            str(_ROOT / "tests" / "fixtures" / "general_prophecy_registry_official_seed_v1.json"),
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 0, r.stderr
    assert "ok" in r.stdout
    assert r.stdout.strip().split()[-1] == "15"


def test_generate_general_prophecy_dry_run() -> None:
    r = subprocess.run(
        [sys.executable, str(_ROOT / "scripts" / "generate_general_prophecy_v1.py"), "--dry-run"],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 0, r.stderr
    assert "ok" in r.stdout
    # default merge: sample (1) + seed_5 (5) + brier_smoke (1) + live_resolved_bootstrap (2) + macro_h2_2026_pack (5)
    assert r.stdout.strip().split()[-1] == "14"


def test_generate_general_prophecy_dry_run_no_default_merge() -> None:
    r = subprocess.run(
        [
            sys.executable,
            str(_ROOT / "scripts" / "generate_general_prophecy_v1.py"),
            "--dry-run",
            "--no-default-merge",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip().split()[-1] == "1"


def test_eval_general_prophecy_brier_stdout_on_fixture() -> None:
    fx = _ROOT / "tests" / "fixtures" / "general_prophecy_registry_sample_v1.json"
    r = subprocess.run(
        [
            sys.executable,
            str(_ROOT / "scripts" / "eval_general_prophecy_brier_score.py"),
            "-i",
            str(fx),
            "--stdout-only",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 0, r.stderr
    assert "general_prophecy_brier_eval_v1" in r.stdout


def test_eval_general_prophecy_brier_no_rows_writes_metrics_only(tmp_path) -> None:
    fx = _ROOT / "tests" / "fixtures" / "general_prophecy_registry_brier_smoke_v1.json"
    out = tmp_path / "brier_no_rows.json"
    r = subprocess.run(
        [
            sys.executable,
            str(_ROOT / "scripts" / "eval_general_prophecy_brier_score.py"),
            "-i",
            str(fx),
            "-o",
            str(out),
            "--no-rows",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 0, r.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert "rows" not in doc
    assert doc.get("metrics", {}).get("n_evaluated", 0) >= 1


def test_eval_general_prophecy_brier_ece_bins_no_rows(tmp_path) -> None:
    fx = _ROOT / "tests" / "fixtures" / "general_prophecy_registry_brier_smoke_v1.json"
    out = tmp_path / "brier_ece.json"
    r = subprocess.run(
        [
            sys.executable,
            str(_ROOT / "scripts" / "eval_general_prophecy_brier_score.py"),
            "-i",
            str(fx),
            "-o",
            str(out),
            "--no-rows",
            "--ece-bins",
            "10",
            "--ece-min-per-tag",
            "1",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 0, r.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    ece = doc.get("metrics", {}).get("ece_binary") or {}
    assert ece.get("n_bins") == 10
    assert isinstance(ece.get("weighted_ece"), (int, float))
    assert len(ece.get("bins") or []) == 10
    by_tag = doc.get("metrics", {}).get("ece_binary_by_domain_tag") or {}
    assert "ci" in by_tag and "math" in by_tag


def test_eval_general_prophecy_brier_on_merged_registry_stdout(tmp_path) -> None:
    import json

    gen = subprocess.run(
        [
            sys.executable,
            str(_ROOT / "scripts" / "generate_general_prophecy_v1.py"),
            "--stdout-only",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert gen.returncode == 0, gen.stderr
    reg = json.loads(gen.stdout)
    assert reg.get("schema") == "general_prophecy_registry_v1"
    assert len(reg.get("questions") or []) == 14

    merged_path = tmp_path / "merged_registry.json"
    merged_path.write_text(gen.stdout, encoding="utf-8")
    r = subprocess.run(
        [
            sys.executable,
            str(_ROOT / "scripts" / "eval_general_prophecy_brier_score.py"),
            "-i",
            str(merged_path),
            "--stdout-only",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert out.get("schema") == "general_prophecy_brier_eval_v1"
    # brier_smoke (1) + live_resolved_bootstrap (2) contribute resolved binary rows
    assert out.get("metrics", {}).get("n_evaluated") == 3
    assert out.get("metrics", {}).get("mean_brier_score") == pytest.approx(0.086133, abs=1e-5)
    bt = out.get("metrics", {}).get("by_prophecy_track") or {}
    assert bt.get("general", {}).get("n_evaluated") == 3
    assert bt.get("general", {}).get("mean_brier_score") == pytest.approx(0.086133, abs=1e-5)


def test_eval_general_prophecy_brier_psychological_state_term_bands(tmp_path) -> None:
    fx = _ROOT / "tests" / "fixtures" / "general_prophecy_registry_auxiliary_covariates_brier_smoke_v1.json"
    out = tmp_path / "brier_psy.json"
    r = subprocess.run(
        [
            sys.executable,
            str(_ROOT / "scripts" / "eval_general_prophecy_brier_score.py"),
            "-i",
            str(fx),
            "-o",
            str(out),
            "--psy-state-min-per-band",
            "2",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 0, r.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    bands = doc.get("metrics", {}).get("by_psychological_state_term_band") or {}
    assert bands.get("split_threshold") == 0.5
    low = bands.get("psychological_state_term_le_0.5") or {}
    high = bands.get("psychological_state_term_gt_0.5") or {}
    assert low.get("n_evaluated") == 2
    assert high.get("n_evaluated") == 2
    assert low.get("mean_brier_score") == pytest.approx(0.26, abs=1e-5)
    assert high.get("mean_brier_score") == pytest.approx(0.25, abs=1e-5)
    rows = doc.get("rows") or []
    assert len(rows) == 4
    assert all("psychological_state_term" in row for row in rows)
