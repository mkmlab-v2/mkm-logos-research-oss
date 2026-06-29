from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["py", *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )


def test_e2e_memory_proof_chain_builds_required_outputs() -> None:
    proc = _run("scripts/run_e2e_memory_proof_chain_v1.py")
    assert proc.returncode == 0, proc.stdout + proc.stderr

    metrics = ROOT / "reports" / "e2e_memory_proof_metrics_latest.json"
    stats = ROOT / "reports" / "e2e_memory_proof_stats_latest.json"
    onepager = ROOT / "docs" / "final" / "artifacts" / "E2E_MEMORY_PROOF_B2B_ONEPAGER_latest.md"
    manifest = ROOT / "reports" / "e2e_memory_proof_repro_manifest_latest.json"

    assert metrics.is_file()
    assert stats.is_file()
    assert onepager.is_file()
    assert manifest.is_file()

    metrics_doc = json.loads(metrics.read_text(encoding="utf-8-sig"))
    stats_doc = json.loads(stats.read_text(encoding="utf-8-sig"))
    manifest_doc = json.loads(manifest.read_text(encoding="utf-8-sig"))

    assert metrics_doc["schema"] == "e2e_memory_proof_metrics_v1"
    assert stats_doc["schema"] == "e2e_memory_proof_stats_v1"
    assert manifest_doc["schema"] == "e2e_memory_proof_repro_manifest_v1"

    m1 = metrics_doc["metrics"]["m1_token_cost"]["input_tokens_avg_per_run"]
    assert int(m1["baseline_a"]) > int(m1["compressed_b"])

    summary = stats_doc["summary"]
    assert float(summary["m1_cost_reduction_ratio"]) > 0.0
    assert int(summary["n_pairs"]) > 0


def test_live_ab_accepts_custom_runs_option() -> None:
    proc = _run("scripts/run_e2e_memory_proof_live_ab_v1.py", "--runs", "4")
    assert proc.returncode == 0, proc.stdout + proc.stderr

    live_metrics = ROOT / "reports" / "e2e_memory_proof_live_metrics_latest.json"
    assert live_metrics.is_file()
    doc = json.loads(live_metrics.read_text(encoding="utf-8-sig"))
    assert doc["schema"] == "e2e_memory_proof_live_metrics_v1"
    assert int(doc["tracks"]["runs_per_arm"]) == 4
