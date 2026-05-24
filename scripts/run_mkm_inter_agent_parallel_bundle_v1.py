#!/usr/bin/env python3
"""Run MKM inter-agent / language parallel workstreams (L1 wire, A2A, routing compare)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/final/artifacts/mkm_inter_agent_parallel_bundle_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(task_id: str, cmd: list[str]) -> dict[str, Any]:
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace")
    return {
        "task_id": task_id,
        "cmd": cmd,
        "exit_code": cp.returncode,
        "ok": cp.returncode == 0,
        "tail": (cp.stdout or cp.stderr or "").strip()[-800:],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--max-workers", type=int, default=6)
    ap.add_argument("--output", type=Path, default=OUT)
    args = ap.parse_args()

    py = sys.executable
    jobs: list[tuple[str, list[str]]] = [
        ("lexicon_rail_demo", [py, "scripts/run_mkm_inter_agent_lexicon_rail_demo_v1.py"]),
        ("l1_lexicon_wire", [py, "scripts/run_mkm_inter_agent_l1_lexicon_wire_demo_v1.py"]),
        (
            "dialogue_trading",
            [
                py,
                "scripts/run_mkm_inter_agent_dialogue_mock_v1.py",
                "--scenario",
                "trading",
                "--turns",
                "4",
                "--summary-out",
                "docs/final/artifacts/mkm_inter_agent_dialogue_mock_trading_summary_latest.json",
            ],
        ),
        (
            "dialogue_health",
            [
                py,
                "scripts/run_mkm_inter_agent_dialogue_mock_v1.py",
                "--scenario",
                "health",
                "--turns",
                "4",
                "--summary-out",
                "docs/final/artifacts/mkm_inter_agent_dialogue_mock_health_summary_latest.json",
            ],
        ),
        (
            "routing_compare_trading",
            [
                py,
                "scripts/run_mkm_inter_agent_dialogue_routing_compare_v1.py",
                "--scenario",
                "trading",
                "--out-json",
                "docs/final/artifacts/mkm_inter_agent_dialogue_routing_compare_trading_latest.json",
            ],
        ),
        (
            "routing_compare_health",
            [
                py,
                "scripts/run_mkm_inter_agent_dialogue_routing_compare_v1.py",
                "--scenario",
                "health",
                "--out-json",
                "docs/final/artifacts/mkm_inter_agent_dialogue_routing_compare_health_latest.json",
            ],
        ),
        ("first_message_emit", [py, "scripts/emit_mkm_inter_agent_first_message_worked_example_v1.py"]),
        ("lexicon_wire_http", [py, "scripts/capture_mkm_inter_agent_lexicon_wire_http_v1.py"]),
        (
            "dialogue_lexicon_dense",
            [
                py,
                "scripts/run_mkm_inter_agent_dialogue_mock_v1.py",
                "--scenario",
                "lexicon_dense",
                "--turns",
                "4",
                "--summary-out",
                "docs/final/artifacts/mkm_inter_agent_dialogue_mock_lexicon_dense_summary_latest.json",
            ],
        ),
        (
            "routing_compare_lexicon_dense",
            [
                py,
                "scripts/run_mkm_inter_agent_dialogue_routing_compare_v1.py",
                "--scenario",
                "lexicon_dense",
                "--out-json",
                "docs/final/artifacts/mkm_inter_agent_dialogue_routing_compare_lexicon_dense_latest.json",
            ],
        ),
        (
            "encoding_status_pytest",
            [py, "-m", "pytest", "tests/test_mkm_inter_agent_wire_m28_v1.py", "-q"],
        ),
        ("lexicon_hit_rate_bench", [py, "scripts/build_mkm_inter_agent_lexicon_hit_rate_bench_v1.py"]),
        (
            "dialogue_wire_first_trading",
            [
                py,
                "scripts/run_mkm_inter_agent_dialogue_wire_first_v1.py",
                "--scenario",
                "trading",
                "--turns",
                "4",
                "--out-json",
                "docs/final/artifacts/mkm_inter_agent_dialogue_wire_first_trading_latest.json",
            ],
        ),
        (
            "dialogue_wire_first_health",
            [
                py,
                "scripts/run_mkm_inter_agent_dialogue_wire_first_v1.py",
                "--scenario",
                "health",
                "--turns",
                "4",
                "--out-json",
                "docs/final/artifacts/mkm_inter_agent_dialogue_wire_first_health_latest.json",
            ],
        ),
        (
            "dialogue_wire_first_lexicon_dense",
            [
                py,
                "scripts/run_mkm_inter_agent_dialogue_wire_first_v1.py",
                "--scenario",
                "lexicon_dense",
                "--turns",
                "4",
                "--out-json",
                "docs/final/artifacts/mkm_inter_agent_dialogue_wire_first_lexicon_dense_latest.json",
            ],
        ),
        ("wire_vs_packet_bench", [py, "scripts/run_mkm_inter_agent_wire_vs_packet_bench_v1.py"]),
        (
            "wire_envelope_schema_validate",
            [py, "scripts/validate_mkm_inter_agent_wire_envelope_v1.py", "--live-probe"],
        ),
        ("ko_wire_bench", [py, "scripts/run_mkm_inter_agent_ko_wire_bench_v1.py"]),
        ("atom_gloss_decode", [py, "scripts/build_mkm_inter_agent_atom_gloss_decode_v1.py"]),
        (
            "wire_session_export",
            [
                py,
                "scripts/export_mkm_inter_agent_wire_session_v1.py",
                "--scenario",
                "trading",
                "--turns",
                "4",
            ],
        ),
        (
            "dialogue_wire_first_live_http",
            [py, "scripts/run_mkm_inter_agent_dialogue_wire_first_live_http_v1.py", "--ephemeral", "--turns", "2"],
        ),
        ("wire_vs_packet_bench_extended", [py, "scripts/run_mkm_inter_agent_wire_vs_packet_bench_extended_v1.py"]),
        (
            "wire_sessions_batch",
            [
                py,
                "scripts/export_mkm_inter_agent_wire_sessions_batch_v1.py",
                "--turns",
                "4",
                "--sidecar-scenarios",
                "health",
            ],
        ),
        ("wire_gloss_session_report", [py, "scripts/build_mkm_inter_agent_wire_gloss_session_report_v1.py"]),
        (
            "wire_session_ops_brief",
            [py, "scripts/build_mkm_inter_agent_wire_session_ops_brief_v1.py", "--no-run-gloss"],
        ),
        ("ko_health_lexicon_coverage", [py, "scripts/build_mkm_inter_agent_ko_health_lexicon_coverage_v1.py"]),
        (
            "wire_jsonl_roundtrip_audit",
            [py, "scripts/audit_mkm_inter_agent_wire_session_jsonl_roundtrip_v1.py", "--no-run-batch"],
        ),
        ("ko_tokenization_experiment", [py, "scripts/build_mkm_inter_agent_ko_tokenization_experiment_v1.py"]),
        ("ko_health_sidecar_wire_demo", [py, "scripts/run_mkm_inter_agent_ko_health_sidecar_wire_demo_v1.py"]),
        ("ko_health_sidecar_encode_capture", [py, "scripts/capture_mkm_inter_agent_ko_health_sidecar_encode_v1.py"]),
        (
            "ko_health_sidecar_batch_chain",
            [py, "scripts/run_mkm_inter_agent_ko_health_sidecar_batch_chain_v1.py", "--turns", "4"],
        ),
        ("ko_morphology_spike", [py, "scripts/build_mkm_inter_agent_ko_morphology_spike_v1.py"]),
        ("m3_public_copy_emit", [py, "scripts/emit_mkm_inter_agent_m3_public_copy_v1.py"]),
        (
            "health_wire_sidecar_dialogue",
            [py, "scripts/capture_mkm_inter_agent_health_wire_sidecar_dialogue_v1.py", "--turns", "4"],
        ),
        (
            "health_wire_sidecar_live_http",
            [py, "scripts/capture_mkm_inter_agent_health_wire_sidecar_live_http_v1.py", "--turns", "2"],
        ),
        (
            "wire_gloss_sidecar_enriched",
            [py, "scripts/build_mkm_inter_agent_wire_gloss_sidecar_enriched_v1.py", "--turns", "4"],
        ),
        ("trackc_ops_dashboard", [py, "scripts/build_mkm_trackc_ops_dashboard_v1.py"]),
        ("rq019_regression_chain", [py, "scripts/run_mkm_inter_agent_rq019_regression_chain_v1.py", "--skip-pytest"]),
        (
            "rq019_weekly_smoke_readiness",
            [py, "scripts/build_mkm_inter_agent_rq019_weekly_smoke_readiness_v1.py"],
        ),
        ("encoding_status", [py, "scripts/build_mkm_inter_agent_encoding_status_v1.py", "--skip-pytest"]),
        ("rq019_ops_slice", [py, "scripts/build_mkm_inter_agent_rq019_ops_slice_v1.py"]),
        ("trackc_rq019_slice", [py, "scripts/build_mkm_inter_agent_trackc_rq019_slice_v1.py"]),
        ("rq019_milestone_index", [py, "scripts/build_mkm_inter_agent_rq019_milestone_artifact_index_v1.py"]),
        (
            "rq019_language_dev_closeout",
            [py, "scripts/build_mkm_inter_agent_rq019_language_dev_closeout_v1.py"],
        ),
        ("wire_profile_v1", [py, "scripts/build_mkm_inter_agent_wire_profile_v1.py"]),
    ]

    sequential_ids = {
        "wire_sessions_batch",
        "wire_gloss_session_report",
        "wire_session_ops_brief",
        "ko_health_lexicon_coverage",
        "wire_jsonl_roundtrip_audit",
        "ko_tokenization_experiment",
        "ko_health_sidecar_wire_demo",
        "ko_health_sidecar_encode_capture",
        "ko_health_sidecar_batch_chain",
        "ko_morphology_spike",
        "m3_public_copy_emit",
        "health_wire_sidecar_dialogue",
        "health_wire_sidecar_live_http",
        "wire_gloss_sidecar_enriched",
        "trackc_ops_dashboard",
        "rq019_regression_chain",
        "rq019_weekly_smoke_readiness",
        "encoding_status",
        "rq019_ops_slice",
        "trackc_rq019_slice",
        "rq019_milestone_index",
        "rq019_language_dev_closeout",
        "wire_profile_v1",
    }
    parallel_jobs = [(tid, cmd) for tid, cmd in jobs if tid not in sequential_ids]
    sequential_jobs = [(tid, cmd) for tid, cmd in jobs if tid in sequential_ids]

    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max(1, args.max_workers)) as pool:
        futs = {pool.submit(_run, tid, cmd): tid for tid, cmd in parallel_jobs}
        for fut in as_completed(futs):
            results.append(fut.result())
    for tid, cmd in sequential_jobs:
        results.append(_run(tid, cmd))
    results.sort(key=lambda r: str(r.get("task_id") or ""))

    pack = {
        "schema": "mkm_inter_agent_parallel_bundle_v2",
        "generated_at_utc": _utc(),
        "research_only": True,
        "boundary_ack": "Parallel B-track / inter-agent research bundle; not live trading or lingua franca completion.",
        "tasks": results,
        "all_ok": all(r.get("ok") for r in results),
        "artifacts": {
            "encoding_status": "docs/final/artifacts/mkm_inter_agent_encoding_status_latest.json",
            "lexicon_rail_demo": "docs/final/artifacts/mkm_inter_agent_lexicon_rail_demo_v1_latest.json",
            "l1_lexicon_wire": "docs/final/artifacts/mkm_inter_agent_l1_lexicon_wire_demo_v1_latest.json",
            "dialogue_trading": "docs/final/artifacts/mkm_inter_agent_dialogue_mock_summary_latest.json",
            "routing_compare_trading": "docs/final/artifacts/mkm_inter_agent_dialogue_routing_compare_trading_latest.json",
            "lexicon_wire_http": "docs/final/artifacts/mkm_inter_agent_lexicon_wire_http_v1_latest.json",
            "dialogue_lexicon_dense": "docs/final/artifacts/mkm_inter_agent_dialogue_mock_lexicon_dense_summary_latest.json",
            "routing_compare_lexicon_dense": "docs/final/artifacts/mkm_inter_agent_dialogue_routing_compare_lexicon_dense_latest.json",
            "lexicon_hit_rate_bench": "docs/final/artifacts/mkm_inter_agent_lexicon_hit_rate_bench_v1_latest.json",
            "sota_map": "docs/final/artifacts/mkm_inter_agent_encoding_sota_map_v1.md",
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    failed = [r["task_id"] for r in results if not r.get("ok")]
    if failed:
        print(f"FAILED: {failed}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
