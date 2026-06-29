"""Regression: P2-G DeepResearch Bench mini harness."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TASKS = ROOT / "tests/fixtures/mkm_deep_research_bench_tasks_v1.json"
BENCH = ROOT / "scripts/run_mkm_deep_research_bench_mini_v1.py"


def test_aggregate_difficulty_gate_blocks_high_threshold() -> None:
    from scripts.run_mkm_deep_research_bench_mini_v1 import aggregate_results

    task_results = [
        {
            "ok": True,
            "citation_pass_rate": 1.0,
            "support_pass_rate": 1.0,
            "difficulty_counts": {"baseline": 4, "challenge": 1},
            "difficulty_pass_metrics": {
                "baseline": {"citation_passed": 4, "support_passed": 4},
                "challenge": {"citation_passed": 1, "support_passed": 1},
            },
            "difficulty_pass_metrics_fallback_used": False,
        }
    ]
    metrics = aggregate_results(
        task_results=task_results,
        min_citation=0.85,
        min_support=0.85,
        require_entry_level=False,
        min_difficulty_challenge_citation=0.8,
        min_difficulty_challenge_support=0.8,
    )
    assert metrics["difficulty_gate_ok"] is True
    metrics_fail = aggregate_results(
        task_results=[
            {
                "ok": True,
                "citation_pass_rate": 1.0,
                "support_pass_rate": 1.0,
                "difficulty_counts": {"baseline": 4, "challenge": 1},
                "difficulty_pass_metrics": {
                    "baseline": {"citation_passed": 4, "support_passed": 4},
                    "challenge": {"citation_passed": 0, "support_passed": 1},
                },
                "difficulty_pass_metrics_fallback_used": False,
            }
        ],
        min_citation=0.85,
        min_support=0.85,
        require_entry_level=False,
        min_difficulty_challenge_citation=0.8,
    )
    assert metrics_fail["difficulty_gate_ok"] is False
    assert metrics_fail["gate_ok"] is False


def test_dr_bench_mini_offline_exit0(tmp_path: Path) -> None:
    out_json = tmp_path / "bench.json"
    out_dir = tmp_path / "artifacts"
    r = subprocess.run(
        [
            sys.executable,
            str(BENCH),
            "--tasks",
            str(TASKS),
            "--offline",
            "--include-router",
            "--out-json",
            str(out_json),
            "--out-dir",
            str(out_dir),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    doc = json.loads(out_json.read_text(encoding="utf-8"))
    assert doc["schema"] == "mkm_deep_research_bench_mini_v1"
    assert doc["ok"] is True
    assert doc["metrics"]["task_count"] == 7
    assert doc["metrics"]["tasks_ok"] == 7
    assert doc["metrics"]["citation_pass_rate_mean"] == 1.0
    assert doc["metrics"]["support_pass_rate_mean"] == 1.0
    assert doc["metrics"]["difficulty_rows_total"]["baseline"] >= 24
    assert doc["metrics"]["difficulty_rows_total"]["challenge"] >= 6
    assert doc["metrics"]["difficulty_pass_rate"]["baseline"]["citation"] == 1.0
    assert doc["metrics"]["difficulty_pass_rate"]["baseline"]["support"] == 1.0
    assert doc["metrics"]["difficulty_pass_rate"]["challenge"]["citation"] == 1.0
    assert doc["metrics"]["difficulty_pass_rate"]["challenge"]["support"] == 1.0
    assert doc["metrics"]["difficulty_entry_mapping"]["fallback_used_task_count"] == 0
    assert doc["metrics"]["difficulty_entry_mapping"]["all_tasks_entry_level"] is True
    assert doc["metrics"]["difficulty_gate_ok"] is True
    assert doc["metrics"]["gate_ok"] is True
    for task in doc["tasks"]:
        assert task["ok"] is True
        assert task["citation_pass_rate"] == 1.0
        assert task["fixture_rows"] >= 5
        assert task["difficulty_counts"]["baseline"] >= 1
        assert task["difficulty_counts"]["challenge"] >= 1
        assert task["difficulty_pass_metrics_source"] == "entries"
        assert task["difficulty_pass_metrics_fallback_used"] is False
        assert task["difficulty_pass_metrics_fallback_reason"] is None
        assert task["difficulty_pass_metrics"]["baseline"]["citation_pass_rate"] == 1.0
        assert task["difficulty_pass_metrics"]["baseline"]["support_pass_rate"] == 1.0
        assert task["difficulty_pass_metrics"]["challenge"]["citation_pass_rate"] == 1.0
        assert task["difficulty_pass_metrics"]["challenge"]["support_pass_rate"] == 1.0


def test_dr_bench_mini_task_ids_unique() -> None:
    spec = json.loads(TASKS.read_text(encoding="utf-8"))
    ids = [t["id"] for t in spec["tasks"]]
    assert len(ids) == len(set(ids))
    assert len(ids) == 7


def test_each_task_fixture_has_at_least_five_rows() -> None:
    spec = json.loads(TASKS.read_text(encoding="utf-8"))
    for task in spec["tasks"]:
        jsonl_path = ROOT / task["jsonl"]
        rows = [line for line in jsonl_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        assert len(rows) >= 5, f"{task['id']} fixture too small: {len(rows)}"


def test_dr_bench_require_entry_level_mode() -> None:
    r = subprocess.run(
        [
            sys.executable,
            str(BENCH),
            "--tasks",
            str(TASKS),
            "--offline",
            "--include-router",
            "--require-entry-level",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    summary = json.loads(r.stdout.strip().splitlines()[-1])
    assert summary["ok"] is True


def test_dr_bench_tcm_task_runs_herbs_extensions(tmp_path: Path) -> None:
    out_json = tmp_path / "bench_tcm.json"
    out_dir = tmp_path / "artifacts"
    r = subprocess.run(
        [
            sys.executable,
            str(BENCH),
            "--tasks",
            str(TASKS),
            "--offline",
            "--include-router",
            "--out-json",
            str(out_json),
            "--out-dir",
            str(out_dir),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    doc = json.loads(out_json.read_text(encoding="utf-8"))
    tcm = next(t for t in doc["tasks"] if t["id"] == "drb_herbs_formulas_tcm")
    assert tcm["ok"] is True
    assert tcm.get("research_plane_match") is True
    ext = tcm["herbs_domain_extensions"]
    assert ext is not None
    assert ext["ok"] is True
    assert ext["steps"]["herbs_extract_chain"]["exit_code"] == 0
    assert ext["steps"]["alias_resolve"]["checks"][0]["ok"] is True


def test_dr_bench_digestion_task_runs_extensions(tmp_path: Path) -> None:
    out_json = tmp_path / "bench_digestion.json"
    out_dir = tmp_path / "artifacts"
    r = subprocess.run(
        [
            sys.executable,
            str(BENCH),
            "--tasks",
            str(TASKS),
            "--offline",
            "--include-router",
            "--out-json",
            str(out_json),
            "--out-dir",
            str(out_dir),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    doc = json.loads(out_json.read_text(encoding="utf-8"))
    dig = next(t for t in doc["tasks"] if t["id"] == "drb_digestion_wiring")
    assert dig["ok"] is True
    assert doc["metrics"].get("digestion_pass_metrics") is not None
    assert doc["metrics"].get("digestion_gate_ok") is True
    ext = dig["digestion_domain_extensions"]
    assert ext is not None
    assert ext["ok"] is True
    assert ext["steps"]["digestion_chain"]["exit_code"] == 0
    checks = ext["steps"]["digestion_checks"]
    assert checks["fact_count"] >= 3
    assert checks["wired_count"] >= 1
    assert checks["gate_ok"] is True
    metrics = checks["digest_pass_metrics"]
    assert metrics["fact_count"] >= 3
    assert metrics["gate_pass_rate"] >= 1.0
