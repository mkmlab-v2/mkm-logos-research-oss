"""GRASP-inspired topology security filter — stub-only defense spike [HYPO]."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
STUB = REPO / "tests/fixtures/logos_verse_4d_topology_stub_v1.jsonl"
BENCH = REPO / "scripts/decomposer/topology_security_filter_v1.py"
REPORT = REPO / "reports/topology_grasp_defense_bench_v1_latest.json"

sys.path.insert(0, str(REPO))

from scripts.decomposer.topology_security_filter_v1 import (  # noqa: E402
    TopologicalDecomposerSanitizer,
    assert_no_canonical_id_leak,
    estimate_grasp_reconstruction_f1,
    jsonl_stub_to_triplets,
    sanitize_topology_triplets,
)


def test_stub_fixture_exists():
    assert STUB.is_file()


def test_id_alignment_and_decoy_injection():
    truth = jsonl_stub_to_triplets(STUB, max_rows=40)
    assert len(truth) >= 10
    package = sanitize_topology_triplets(truth, decoy_ratio=0.15)
    sanitized = package["sanitized_triplets"]
    real = [t for t in sanitized if not t.get("is_decoy")]
    decoys = [t for t in sanitized if t.get("is_decoy")]

    assert len(real) == len(truth)
    assert len(decoys) >= int(len(truth) * 0.15)
    assert package["decoy_ratio_applied"] >= 0.14

    instance_ids = [t["instance_id"] for t in real]
    assert len(instance_ids) == len(set(instance_ids))

    canonical = {t["src"] for t in truth} | {t["dst"] for t in truth}
    assert not assert_no_canonical_id_leak(sanitized, canonical)


def test_grasp_reconstruction_f1_below_gate_on_stub_sample():
    truth = jsonl_stub_to_triplets(STUB, max_rows=120)
    package = sanitize_topology_triplets(truth, decoy_ratio=0.15)
    metrics = estimate_grasp_reconstruction_f1(truth, package["sanitized_triplets"])
    assert metrics["f1"] <= 0.15, metrics


def test_session_reset_breaks_virtual_id_replay():
    truth = jsonl_stub_to_triplets(STUB, max_rows=5)
    san_a = TopologicalDecomposerSanitizer(decoy_ratio=0.0)
    san_b = TopologicalDecomposerSanitizer(decoy_ratio=0.0)
    out_a = san_a.sanitize(truth)
    san_b.reset_session()
    out_b = san_b.sanitize(truth)
    assert out_a[0]["src"] != out_b[0]["src"]


def test_grasp_reconstruction_f1_full_stub_gate():
    truth = jsonl_stub_to_triplets(STUB, max_rows=None)
    assert len(truth) >= 500
    package = sanitize_topology_triplets(truth, decoy_ratio=0.15)
    metrics = estimate_grasp_reconstruction_f1(truth, package["sanitized_triplets"])
    assert metrics["f1"] <= 0.15, metrics


def test_bench_cli_exit_zero():
    r = subprocess.run(
        [
            sys.executable,
            str(BENCH),
            "--max-rows",
            "120",
            "--decoy-ratio",
            "0.15",
            "--f1-gate",
            "0.15",
        ],
        cwd=str(REPO),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr
    assert REPORT.is_file()
    doc = json.loads(REPORT.read_text(encoding="utf-8"))
    assert doc["schema"] == "topology_security_sanitize_v1"
    assert doc["send_gate"] == "HOLD"
    assert doc["gate_ok"] is True
    assert doc["grasp_defense_metrics"]["f1"] <= 0.15
