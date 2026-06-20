"""E2E shallow router -> semantic_rag_bridge smoke [HYPO]."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CHAIN_OUT = ROOT / "reports/ollama_shallow_to_semantic_rag_e2e_v1_latest.json"
BUNDLE_OUT = ROOT / "docs/final/artifacts/semantic_rag_bridge_insight_bundle_shallow_e2e_v1_latest.json"
MATRIX_OUT = ROOT / "reports/ollama_shallow_e2e_domain_matrix_v1_latest.json"
DOMAIN_EXAMPLES = ROOT / "tests/fixtures/ollama_shallow_e2e_domain_examples_v1.json"


def test_shallow_to_semantic_rag_e2e_smoke_exit0() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_ollama_shallow_to_semantic_rag_e2e_v1.py"),
            "--include-deep-chain-dry-run",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    chain = json.loads(CHAIN_OUT.read_text(encoding="utf-8"))
    assert chain.get("schema") == "ollama_shallow_to_semantic_rag_e2e_v1"
    assert chain.get("send_gate") == "HOLD"
    assert chain.get("steps", {}).get("handoff", {}).get("ok") is True
    assert chain.get("steps", {}).get("semantic_rag_bridge_bundle", {}).get("ok") is True
    assert chain.get("steps", {}).get("deep_chain_dry_run", {}).get("ok") is True
    bundle = json.loads(BUNDLE_OUT.read_text(encoding="utf-8"))
    assert bundle.get("schema") == "semantic_rag_bridge_insight_bundle_v1"
    assert bundle.get("lens_route", {}).get("lens_id") == "logos"


def test_shallow_e2e_domain_examples_matrix_exit0() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_ollama_shallow_to_semantic_rag_e2e_v1.py"),
            "--run-domain-examples",
            str(DOMAIN_EXAMPLES),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    matrix = json.loads(MATRIX_OUT.read_text(encoding="utf-8"))
    assert matrix.get("schema") == "ollama_shallow_e2e_domain_matrix_v1"
    assert matrix.get("all_ok") is True
    assert len(matrix.get("results") or []) == 3
    for row in matrix["results"]:
        assert row.get("ok") is True
        assert row.get("actual_lens_id") == row.get("expected_lens_id")
        assert row.get("actual_calibration_kind") == row.get("expected_calibration_kind")
        assert row.get("bundle_validation_ok") is True


@pytest.mark.skipif(
    not os.getenv("MKM_SHALLOW_E2E_DEEP_LIVE"),
    reason="set MKM_SHALLOW_E2E_DEEP_LIVE=1 to run live deep chain (slow)",
)
def test_shallow_e2e_deep_chain_live_exit0() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_ollama_shallow_to_semantic_rag_e2e_v1.py"),
            "--include-deep-chain-live",
            "--query",
            "욥이 고난을 받은 이유",
            "--query-id",
            "job_suffering_reason",
            "--deep-chain-timeout-sec",
            "360",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=420,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    chain = json.loads(CHAIN_OUT.read_text(encoding="utf-8"))
    live = chain.get("steps", {}).get("deep_chain_live") or {}
    assert live.get("ok") is True
    assert live.get("panorama_preflight_ok") is True
