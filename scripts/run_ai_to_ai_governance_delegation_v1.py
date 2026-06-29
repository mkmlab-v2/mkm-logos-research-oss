#!/usr/bin/env python3
"""AI-to-AI governance delegation v1 — sequential AUTO chain (meta envelope + ops memory).

research_only · Track A / live / apply-active / MISSION_LOG write forbidden from this script.
SSOT summary: reports/ai_to_ai_governance_delegation_v1_latest.json
Approval map: reports/delegation_ai_to_ai_governance_approval_map_v1_latest.json
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
OUT_SUMMARY = ROOT / "reports/ai_to_ai_governance_delegation_v1_latest.json"
OUT_MAP = ROOT / "reports/delegation_ai_to_ai_governance_approval_map_v1_latest.json"
META_FIXTURE = (
    ROOT / "docs/final/artifacts/fixtures/mkm_meta_layer_turn_envelope_v1.example.json"
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str], *, cwd: Path = ROOT) -> dict[str, Any]:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return {
        "cmd": cmd,
        "exit_code": proc.returncode,
        "stdout_tail": (proc.stdout or "")[-2000:],
        "stderr_tail": (proc.stderr or "")[-1000:],
    }


def _node(
    *,
    node_id: str,
    name: str,
    approval: str,
    status: str,
    exit_code: int | None,
    evidence: str | None = None,
    skip_reason: str | None = None,
    facts: dict[str, Any] | None = None,
    run: dict[str, Any] | None = None,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "id": node_id,
        "name": name,
        "approval": approval,
        "status": status,
        "exit_code": exit_code,
        "evidence": evidence,
        "skip_reason": skip_reason,
    }
    if facts:
        out["facts"] = facts
    if run:
        out["run"] = run
    return out


def lane_p0() -> dict[str, Any]:
    ps1 = ROOT / "scripts/verify_p0_constitution_gate_paths.ps1"
    r = _run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(ps1),
        ]
    )
    status = "done" if r["exit_code"] == 0 else "failed"
    return _node(
        node_id="0",
        name="p0_constitution_paths",
        approval="AUTO",
        status=status,
        exit_code=r["exit_code"],
        evidence="scripts/verify_p0_constitution_gate_paths.ps1",
        run=r,
    )


def lane_meta_pytest() -> dict[str, Any]:
    r = _run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/test_mkm_meta_layer_envelope_v1.py",
            "-q",
        ]
    )
    status = "done" if r["exit_code"] == 0 else "failed"
    return _node(
        node_id="1",
        name="meta_layer_envelope_pytest",
        approval="AUTO",
        status=status,
        exit_code=r["exit_code"],
        evidence="tests/test_mkm_meta_layer_envelope_v1.py",
        run=r,
    )


def lane_meta_validate_fixture() -> dict[str, Any]:
    r = _run(
        [
            sys.executable,
            str(ROOT / "scripts/mkm_meta_layer_envelope_v1.py"),
            "validate",
            "--json-file",
            str(META_FIXTURE),
        ]
    )
    status = "done" if r["exit_code"] == 0 else "failed"
    return _node(
        node_id="2",
        name="meta_layer_envelope_validate_fixture",
        approval="AUTO",
        status=status,
        exit_code=r["exit_code"],
        evidence=str(META_FIXTURE.relative_to(ROOT)).replace("\\", "/"),
        run=r,
    )


def lane_ops_memory_routine(*, skip_web_ops_overlay: bool) -> dict[str, Any]:
    ps1 = ROOT / "scripts/Invoke-MkmOpsMemoryIndexRoutine_v1.ps1"
    cmd = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(ps1),
        "-IncludeA2aPilot",
    ]
    if skip_web_ops_overlay:
        cmd.append("-SkipWebOpsOverlay")
    r = _run(cmd)
    bench_path = ROOT / "reports/mkm_ops_memory_index_token_bench_v1_latest.json"
    pilot_path = ROOT / "docs/final/artifacts/mkm_chat_resume_a2a_pilot_v1_latest.json"
    bench: dict[str, Any] = {}
    pilot: dict[str, Any] = {}
    if bench_path.is_file():
        try:
            bench = json.loads(bench_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            bench = {}
    if pilot_path.is_file():
        try:
            pilot = json.loads(pilot_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pilot = {}
    status = "done" if r["exit_code"] == 0 else "failed"
    return _node(
        node_id="3",
        name="ops_memory_index_routine_a2a",
        approval="AUTO",
        status=status,
        exit_code=r["exit_code"],
        evidence="storage/meta/mkm_ops_memory_index_v1.json",
        facts={
            "inject_off_tokens": bench.get("inject_off_tokens"),
            "a2a_inject_tokens": pilot.get("inject_tokens"),
            "a2a_decision": pilot.get("decision"),
        },
        run=r,
    )


def lane_ops_memory_pytest() -> dict[str, Any]:
    r = _run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/test_mkm_ops_memory_index_v1.py",
            "-q",
        ]
    )
    status = "done" if r["exit_code"] == 0 else "failed"
    return _node(
        node_id="4",
        name="ops_memory_index_pytest",
        approval="AUTO",
        status=status,
        exit_code=r["exit_code"],
        evidence="tests/test_mkm_ops_memory_index_v1.py",
        run=r,
    )


STOP_NODES: list[dict[str, Any]] = [
    _node(
        node_id="S1",
        name="gcp_vertex_credit_burn",
        approval="STOP",
        status="skipped",
        exit_code=None,
        skip_reason="cost_tier_human_only",
        evidence="scripts/run_gcp_free_trial_vertex_credit_burn_v1.py",
    ),
    _node(
        node_id="S2",
        name="track_c_meta_fusion_live_append",
        approval="STOP",
        status="skipped",
        exit_code=None,
        skip_reason="MetaLayerEnvelopePath requires explicit path; not auto on all output",
        evidence="scripts/Invoke-TrackCMacroDailyFusion_v1.ps1",
    ),
    _node(
        node_id="S3",
        name="integrated_governance_full_rebuild",
        approval="STOP",
        status="skipped",
        exit_code=None,
        skip_reason="deps_gated_heavy; AthenaBundle lane",
        evidence="scripts/invoke_build_integrated_governance_if_deps_present_v1.py",
    ),
    _node(
        node_id="S4",
        name="node_v2_ops_memory_wire",
        approval="STOP",
        status="skipped",
        exit_code=None,
        skip_reason="NODE v2 HOLD per one-pager",
    ),
    _node(
        node_id="S5",
        name="apply_active_or_live",
        approval="STOP",
        status="skipped",
        exit_code=None,
        skip_reason="human_signoff_required",
    ),
]


def _build_approval_map(nodes: list[dict[str, Any]], *, chain_ok: bool) -> dict[str, Any]:
    return {
        "schema": "delegation_ai_to_ai_governance_approval_map_v1",
        "generated_at_utc": _utc_now(),
        "project_id": "ai_to_ai_governance_delegation_v1",
        "hypo_label": "[HYPO]",
        "research_only": True,
        "track_a_active_write": False,
        "delegation_status": "auto_complete" if chain_ok else "partial_fail",
        "ssot": {
            "mission_log_section": "MISSION_LOG.md §AI-to-AI 거버넌스 위임",
            "runner": "scripts/run_ai_to_ai_governance_delegation_v1.py",
            "persona": "Invoke-MkmPersonaHealth_v1.ps1 -Persona AiToAiGovernanceDelegation",
            "canvas": "canvases/delegation-ai-to-ai-governance.canvas.tsx",
            "resume_trigger": "@MISSION_LOG.md 미션로그 이어서 — AI-to-AI 거버넌스",
        },
        "global_stop_rules": [
            "apply-active without human sign-off",
            "live trading ON / trading_go_no_go override",
            "MISSION_LOG concurrent write from multiple chats",
            "gcp_vertex_credit_burn without explicit tier approval",
            "meta envelope auto-append on all agent turns",
            "MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json write",
        ],
        "nodes": [
            {
                "id": n["id"],
                "name": n["name"],
                "approval": n["approval"],
                "status": n["status"],
                "exit_code": n.get("exit_code"),
                "evidence": n.get("evidence"),
                "skip_reason": n.get("skip_reason"),
            }
            for n in nodes
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="AI-to-AI governance delegation AUTO chain")
    ap.add_argument("--dry-run", action="store_true", help="Plan only; no subprocess")
    ap.add_argument("--skip-p0", action="store_true")
    ap.add_argument("--skip-web-ops-overlay", action="store_true")
    ap.add_argument(
        "--parallel-pytest",
        action="store_true",
        help="Run meta + ops memory pytest in parallel (after validate)",
    )
    args = ap.parse_args()

    auto_plan: list[tuple[str, Callable[[], dict[str, Any]]]] = []
    if not args.skip_p0:
        auto_plan.append(("p0", lane_p0))
    auto_plan.append(("meta_pytest", lane_meta_pytest))
    auto_plan.append(("meta_validate", lane_meta_validate_fixture))
    auto_plan.append(
        (
            "ops_routine",
            lambda: lane_ops_memory_routine(skip_web_ops_overlay=args.skip_web_ops_overlay),
        )
    )
    auto_plan.append(("ops_pytest", lane_ops_memory_pytest))

    if args.dry_run:
        payload = {
            "schema": "ai_to_ai_governance_delegation_v1",
            "generated_at_utc": _utc_now(),
            "dry_run": True,
            "auto_lanes_planned": [p[0] for p in auto_plan],
            "stop_nodes": [n["id"] for n in STOP_NODES],
            "parallel_pytest": args.parallel_pytest,
        }
        OUT_SUMMARY.parent.mkdir(parents=True, exist_ok=True)
        OUT_SUMMARY.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0

    auto_nodes: list[dict[str, Any]] = []

    if args.parallel_pytest:
        sequential_first = [p for p in auto_plan if p[0] in ("p0", "meta_validate", "ops_routine")]
        parallel_keys = {"meta_pytest", "ops_pytest"}
        parallel_plan = [p for p in auto_plan if p[0] in parallel_keys]
        for _key, fn in sequential_first:
            auto_nodes.append(fn())
            if auto_nodes[-1]["status"] == "failed":
                break
        else:
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = {pool.submit(fn): key for key, fn in parallel_plan}
                results: dict[str, dict[str, Any]] = {}
                for fut in as_completed(futures):
                    results[futures[fut]] = fut.result()
                for key, _fn in parallel_plan:
                    auto_nodes.append(results[key])
    else:
        for _key, fn in auto_plan:
            auto_nodes.append(fn())
            if auto_nodes[-1]["status"] == "failed":
                break

    all_nodes = auto_nodes + STOP_NODES
    hard_fail = any(n["approval"] == "AUTO" and n["status"] == "failed" for n in auto_nodes)
    chain_ok = not hard_fail

    summary = {
        "schema": "ai_to_ai_governance_delegation_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "track_a_active_write": False,
        "chain_ok": chain_ok,
        "parallel_pytest": args.parallel_pytest,
        "auto_nodes": auto_nodes,
        "stop_nodes": STOP_NODES,
    }
    approval = _build_approval_map(all_nodes, chain_ok=chain_ok)

    OUT_SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    OUT_SUMMARY.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    OUT_MAP.write_text(json.dumps(approval, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(json.dumps({"ok": chain_ok, "out": str(OUT_SUMMARY.relative_to(ROOT))}, ensure_ascii=False))
    return 1 if hard_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
