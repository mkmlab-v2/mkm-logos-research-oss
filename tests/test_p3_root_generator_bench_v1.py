"""P3-Root-Generator bench v1 — contract, runner, gate (B-track)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
CONTRACT = REPO / "docs/final/artifacts/P3_ROOT_GENERATOR_BENCH_CONTRACT_V1.json"
BENCH = REPO / "scripts/run_p3_root_generator_bench_v1.py"
GATE = REPO / "scripts/check_p3_root_generator_bench_gate_v1.py"
REPORT = REPO / "reports/p3_root_generator_bench_v1_latest.json"
GATE_REPORT = REPO / "reports/p3_root_generator_bench_gate_v1_latest.json"
HANGUL_CANDIDATE = (
    REPO
    / "reports/constitution/btrack_pilot"
    / "master_codebook_lexicon_v1_41676_hangul_curated_export_candidate_v3_golden40_evidence.json"
)


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(REPO), capture_output=True, text=True)


def test_contract_shape():
    doc = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert doc["schema"] == "p3_root_generator_bench_contract_v1"
    assert doc["research_only"] is True
    assert "extension" in (doc.get("profiles") or {})


def test_bench_runner_smoke():
    r = _run([sys.executable, str(BENCH), "--compression-sample", "3"])
    assert r.returncode == 0, r.stderr
    assert REPORT.is_file()
    doc = json.loads(REPORT.read_text(encoding="utf-8"))
    assert doc["schema"] == "p3_root_generator_bench_v1"
    assert doc["send_gate"] == "HOLD"
    assert "baseline" in doc and "candidate" in doc
    assert doc["baseline"].get("router_probe") is not None
    assert doc["comparison"].get("router_probe_lexicon_hit_rate_delta") is not None


def test_gate_hold_on_baseline_self_compare():
    _run([sys.executable, str(BENCH), "--compression-sample", "2"])
    r = _run([sys.executable, str(GATE)])
    assert r.returncode == 0
    doc = json.loads(GATE_REPORT.read_text(encoding="utf-8"))
    assert doc["decision"] == "HOLD"
    assert "candidate_same_as_baseline" in doc.get("reasons", [])


@pytest.mark.skipif(not HANGUL_CANDIDATE.is_file(), reason="hangul export candidate not built")
def test_extension_candidate_bench_runs():
    r = _run(
        [
            sys.executable,
            str(BENCH),
            "--profile",
            "extension",
            "--candidate-lexicon",
            str(HANGUL_CANDIDATE),
            "--compression-sample",
            "2",
        ]
    )
    assert r.returncode == 0, r.stderr
    doc = json.loads(REPORT.read_text(encoding="utf-8"))
    assert doc["comparison"]["same_lexicon"] is False
    assert doc["comparison"]["atom_retention"]["retention_rate"] >= 0.99
