"""Smoke: Prism pinset swap selector (B-track)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_select_pinset_py_coding_max_three() -> None:
    from scripts.sandbox.build_prism_pinset_swap_v1 import select_pinset

    pinset = select_pinset(
        registry_path=ROOT / "docs/final/MKM12_PRISM_INDEX_REGISTRY_V1.json",
        contract_path=ROOT / "experiments/no_guard_limit_test/prism_pinset_swap_contract_v1.json",
        task_profile="py_coding",
        context_text="Fix scripts/sandbox compression pytest evaluate_report",
        file_hint="code_context",
    )
    entries = pinset.get("entries") or []
    assert 1 <= len(entries) <= 3
    ids = {str(e.get("id")) for e in entries}
    assert "prism_constitution_implementation_facts" in ids
    for ent in entries:
        assert ent.get("prism_axis") in ("S", "K")
        assert ent.get("path")
        assert ent.get("summary_ko")


def test_format_block_token_estimate() -> None:
    from scripts.sandbox.build_prism_pinset_swap_v1 import (
        estimate_pinset_tokens,
        format_pinset_block,
        select_pinset,
    )

    pinset = select_pinset(
        registry_path=ROOT / "docs/final/MKM12_PRISM_INDEX_REGISTRY_V1.json",
        contract_path=ROOT / "experiments/no_guard_limit_test/prism_pinset_swap_contract_v1.json",
        task_profile="py_coding",
        context_text="cursor coding compress",
    )
    block = format_pinset_block(pinset)
    assert "[PRISM_PINSET v1" in block
    assert estimate_pinset_tokens(block) > 0


def test_build_cli_writes_json() -> None:
    out = ROOT / "experiments/no_guard_limit_test/results/prism_pinset_swap_test.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/sandbox/build_prism_pinset_swap_v1.py"),
            "--context-text",
            "py scripts compression",
            "--out-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "prism_pinset_swap_v1"
    assert len(doc.get("entries") or []) <= 3


def test_prism_pinset_bench_dry_run() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/sandbox/run_prism_pinset_coding_bench_v1.py"),
            "--dry-run",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
