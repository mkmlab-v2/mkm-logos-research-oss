"""[HYPO] Coordinator science kernel v2 smoke."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHAIN = ROOT / "scripts/run_nextgen_coordinator_science_kernel_v2_chain_v1.py"
OUT = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_coordinator_science_kernel_v2_chain_v1_latest.json"
)


def test_coordinator_loss_formula():
    from scripts.nextgen_coordinator_science_loss_v1 import compute_coordinator_loss

    low = compute_coordinator_loss(
        saving=0.5, jaccard=0.89, byte_exact_violation=0.0, disagreement=0.1
    )
    high = compute_coordinator_loss(
        saving=0.4, jaccard=0.80, byte_exact_violation=1.0, disagreement=0.2
    )
    assert high > low


def test_lens_disagreement_nonzero_on_mixed_text():
    from scripts.nextgen_coordinator_science_loss_v1 import lens_disagreement_proxy

    raw = (
        "entropy symmetry conservation sasang taeeum myeongni 사주 팔자 bible covenant "
        "tensor field equilibrium regime analysis policy track"
    )
    logos = frozenset({"bible", "covenant", "policy", "track"})
    sci = frozenset({"entropy", "symmetry", "tensor", "field", "equilibrium"})
    sas = frozenset({"sasang", "taeeum"})
    mye = frozenset({"myeongni", "사주", "팔자"})
    d = lens_disagreement_proxy(
        raw,
        keep_ratio=0.86,
        logos_terms=logos,
        science_terms=sci,
        sasang_terms=sas,
        science_weight_scale=1.0,
        myeongni_terms=mye,
        disagreement_keep_ratio=0.45,
    )
    assert d > 0.0


def test_partition_lens_terms_myeongni_bucket():
    from scripts.nextgen_coordinator_science_loss_v1 import partition_lens_terms

    all_t = frozenset({"entropy", "sasang", "myeongni", "bible"})
    sci = frozenset({"entropy"})
    logos, science, sasang, myeongni = partition_lens_terms(all_t, sci)
    assert "entropy" in science
    assert "sasang" in sasang
    assert "myeongni" in myeongni
    assert "bible" in logos


def test_coordinator_kernel_v2_chain_smoke_exit0():
    r = subprocess.run(
        [sys.executable, str(CHAIN), "--smoke"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert r.returncode == 0, r.stderr[-2000:]
    doc = json.loads(OUT.read_text(encoding="utf-8-sig"))
    assert doc["schema"] == "nextgen_coordinator_science_kernel_v2_chain_v1"
    assert doc["closure_ok"] is True
    assert doc["track_a_active_write"] is False
