"""[HYPO] Science prior sidecar spec + chain smoke."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC = ROOT / "experiments/nextgen_clean_slate_cpu_v1/SCIENCE_PRIOR_SIDECAR_SPEC_V1.json"
CHAIN = ROOT / "scripts/run_nextgen_science_prior_sidecar_chain_v1.py"
CHAIN_OUT = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_science_prior_sidecar_chain_v1_latest.json"
)


def test_science_spec_loads_terms():
    from scripts.nextgen_science_prior_terms_v1 import load_science_prior_terms

    terms, meta = load_science_prior_terms(root=ROOT, spec_path=SPEC)
    assert meta.get("present") is True
    assert len(terms) >= 8
    assert "entropy" in terms or "에너지" in terms


def test_science_prior_sidecar_chain_exit0():
    r = subprocess.run(
        [sys.executable, str(CHAIN)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert r.returncode == 0, r.stderr[-3000:]
    doc = json.loads(CHAIN_OUT.read_text(encoding="utf-8-sig"))
    assert doc["schema"] == "nextgen_science_prior_sidecar_chain_v1"
    assert doc["closure_ok"] is True
    assert doc["track_a_active_write"] is False
    raw = doc.get("raw") or {}
    assert raw.get("trilane_hybrid", {}).get("byte_exact_subset_parity") == 1.0
