"""Smoke: phase-3 dynamic pinset v2, corpus isolation, proxy meta wire."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "experiments/no_guard_limit_test/results"


def test_py_coding_dynamic_differs_from_fixed_on_code_context() -> None:
    from scripts.sandbox.build_prism_pinset_swap_v1 import select_pinset

    registry = ROOT / "docs/final/MKM12_PRISM_INDEX_REGISTRY_V1.json"
    contract = ROOT / "experiments/no_guard_limit_test/prism_pinset_swap_contract_v1.json"
    ctx = "def should_bypass_compression(token_in): evaluate_report(doc, use_master_codebook_lexicon_v1=True)"

    fixed = select_pinset(
        registry_path=registry,
        contract_path=contract,
        task_profile="py_coding",
        selection_mode="fixed_preferred",
    )
    dynamic = select_pinset(
        registry_path=registry,
        contract_path=contract,
        task_profile="py_coding_dynamic",
        context_text=ctx,
        file_hint="code_context",
        selection_mode="context_scored",
    )
    fixed_ids = {e.get("id") for e in fixed.get("entries") or []}
    dynamic_ids = {e.get("id") for e in dynamic.get("entries") or []}
    assert fixed_ids != dynamic_ids


def test_coding_proxy_meta_wire_off_by_default() -> None:
    import os

    from scripts.sandbox.coding_proxy_meta_channel_v1 import coding_proxy_compress_with_meta

    os.environ.pop("MKM_PRISM_META_CHANNEL_BTRACK", None)
    out = coding_proxy_compress_with_meta(
        "fix pytest",
        {"strategy": "A", "intensity": "extreme"},
        lane="user_query_short",
        lane_intensity={"user_query_short": "ultra"},
        enable_meta=False,
    )
    assert out.get("meta_channel") is None


def test_phase3_bench_dry_runs() -> None:
    for script, name in (
        ("run_prism_dynamic_pinset_heavy_bench_v1.py", "b2v2_test.json"),
        ("run_prism_corpus_isolation_bench_v1.py", "corp_iso_test.json"),
        ("run_prism_proxy_meta_wire_bench_v1.py", "proxy_meta_wire_test.json"),
        ("run_prism_dynamic_pinset_bench_v1.py", "dynamic_pinset_test.json"),
    ):
        proc = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/sandbox" / script),
                "--dry-run",
                "--out-json",
                str(RESULTS / name),
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == 0, proc.stderr
