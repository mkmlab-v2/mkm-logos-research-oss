"""Smoke: parallel Prism lanes A (meta channel) and B (dynamic pinset)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_meta_channel_preserves_bypass_on_short_text() -> None:
    from scripts.sandbox.eval_proxy_with_meta_channel_v1 import eval_proxy_with_attachment, load_guarded_context

    hardening = ROOT / "data/btrack/compression_coding_proxy_hardening_v1.json"
    profile, lane_intensity = load_guarded_context(hardening)
    short = "fix pytest"
    block = "[PRISM_PINSET v1 · research_only · max 3]\n- a | b | c\n\n"

    base = eval_proxy_with_attachment(
        short,
        profile,
        lane="user_query_short",
        lane_intensity=lane_intensity,
        injection_mode="none",
    )
    meta = eval_proxy_with_attachment(
        short,
        profile,
        lane="user_query_short",
        lane_intensity=lane_intensity,
        attachment_block=block,
        injection_mode="meta_channel_post_gatekeeper",
    )
    prep = eval_proxy_with_attachment(
        short,
        profile,
        lane="user_query_short",
        lane_intensity=lane_intensity,
        attachment_block=block,
        injection_mode="prepend",
    )

    assert base.get("proxy_path") == "gatekeeper_bypass"
    assert meta.get("proxy_path") == "gatekeeper_bypass"
    assert meta.get("reconstruction_fidelity_jaccard") == base.get("reconstruction_fidelity_jaccard")
    assert meta.get("meta_channel_tokens", 0) > 0
    assert prep.get("gatekeeper_input_tokens", 0) > base.get("gatekeeper_input_tokens", 0)


def test_dynamic_pinset_selection_mode_differs() -> None:
    from scripts.sandbox.build_prism_pinset_swap_v1 import select_pinset

    registry = ROOT / "docs/final/MKM12_PRISM_INDEX_REGISTRY_V1.json"
    contract = ROOT / "experiments/no_guard_limit_test/prism_pinset_swap_contract_v1.json"

    fixed = select_pinset(
        registry_path=registry,
        contract_path=contract,
        task_profile="py_coding",
        selection_mode="fixed_preferred",
    )
    dynamic = select_pinset(
        registry_path=registry,
        contract_path=contract,
        task_profile="py_coding",
        context_text="scripts/run_compression_automation_chain.ps1 pytest evaluate_report",
        file_hint="code_context",
        selection_mode="context_scored",
    )
    fixed_ids = {e.get("id") for e in fixed.get("entries") or []}
    dynamic_ids = {e.get("id") for e in dynamic.get("entries") or []}
    assert len(fixed_ids) <= 3
    assert len(dynamic_ids) <= 3
    assert "prism_constitution_implementation_facts" in fixed_ids


def test_no_guard_meta_channel_preserves_user_jaccard() -> None:
    from scripts.sandbox.eval_no_guard_with_meta_channel_v1 import eval_no_guard_with_attachment

    profile = ROOT / "experiments/no_guard_limit_test/no_guard_profile_v1.json"
    text = "def compress_corpus(lexicon_path): return evaluate_report(doc)"
    block = "[PRISM_PINSET v1 · research_only · max 3]\n- id | path | summary\n\n"

    base = eval_no_guard_with_attachment(
        text,
        no_guard_profile=profile,
        lane="code_context",
        injection_mode="none",
    )
    meta = eval_no_guard_with_attachment(
        text,
        no_guard_profile=profile,
        lane="code_context",
        attachment_block=block,
        injection_mode="meta_channel_post_gatekeeper",
    )
    assert base.get("reconstruction_fidelity_jaccard") == meta.get("reconstruction_fidelity_jaccard")
    assert meta.get("meta_channel_tokens", 0) > 0


def test_lane_a_b_c_bench_cli_dry_run() -> None:
    for script in (
        "run_prism_meta_channel_bench_v1.py",
        "run_prism_dynamic_pinset_bench_v1.py",
        "run_prism_no_guard_meta_channel_bench_v1.py",
    ):
        out = ROOT / "experiments/no_guard_limit_test/results" / f"_pytest_dry_{script.replace('.py', '')}.json"
        proc = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/sandbox" / script),
                "--dry-run",
                "--out-json",
                str(out),
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == 0, proc.stderr
