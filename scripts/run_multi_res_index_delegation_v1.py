#!/usr/bin/env python3
"""Multi-Res Index delegation v1 — sequential AUTO chain (commercial shape, B-track).

research_only · Track A / live / apply-active / alwaysApply mutation forbidden.
Approval map: reports/delegation_multi_res_index_approval_map_v1_latest.json
Summary: reports/multi_res_index_delegation_v1_latest.json
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT_MAP = ROOT / "reports/delegation_multi_res_index_approval_map_v1_latest.json"
OUT_SUMMARY = ROOT / "reports/multi_res_index_delegation_v1_latest.json"

PY = sys.executable


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_map() -> dict[str, Any]:
    return json.loads(OUT_MAP.read_text(encoding="utf-8-sig"))


def _save_map(doc: dict[str, Any]) -> None:
    doc["generated_at_utc"] = _utc_now()
    OUT_MAP.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _run(cmd: list[str]) -> dict[str, Any]:
    proc = subprocess.run(
        cmd,
        cwd=str(ROOT),
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


def _node_by_id(doc: dict[str, Any], node_id: str) -> dict[str, Any] | None:
    for n in doc.get("nodes", []):
        if n.get("id") == node_id:
            return n
    return None


def _deps_satisfied(doc: dict[str, Any], node: dict[str, Any]) -> bool:
    for dep in node.get("depends_on") or []:
        dep_node = _node_by_id(doc, dep)
        if not dep_node or dep_node.get("status") != "done":
            return False
    return True


def _evidence_exists(node: dict[str, Any]) -> bool:
    ev = node.get("evidence")
    if not ev:
        return False
    return (ROOT / ev).is_file()


def _node_done(node: dict[str, Any], *, extra_check: bool = True) -> bool:
    if not _evidence_exists(node):
        return False
    if node["id"] == "W3.1":
        idx = ROOT / "storage/meta/mkm_ops_memory_index_v1.json"
        if not idx.is_file():
            return False
        doc = json.loads(idx.read_text(encoding="utf-8-sig"))
        return "prism_ops_fills_multi_res_summary" in (doc.get("nodes") or {})
    if node["id"] == "R3":
        dash = ROOT / "docs/final/artifacts/mkm_trackc_ops_dashboard_latest.json"
        if not dash.is_file():
            return False
        doc = json.loads(dash.read_text(encoding="utf-8-sig"))
        return "multi_res_fills_summary" in (doc.get("trackc") or {})
    return extra_check


AUTO_RUNNERS: dict[str, list[str]] = {
    "W1.3": [PY, "-m", "pytest", "tests/test_multi_res_index_v1.py", "-q"],
    "W1.4": [PY, "scripts/update_multi_res_promotion_manifest_v1.py"],
    "W2.1": [PY, "scripts/multi_res_fills_join_v1.py"],
    "W2.2": [PY, "-m", "pytest", "tests/test_multi_res_fills_join_v1.py", "-q"],
    "W2.3": [PY, "scripts/build_multi_res_fills_token_bench_v1.py"],
    "W3.1": [PY, "scripts/build_mkm_ops_memory_fills_overlay_v1.py"],
    "W3.2": [
        PY,
        "scripts/check_mkm_ops_memory_must_keep_gate_v1.py",
        "--phase",
        "source",
        "--node-id",
        "prism_ops_fills_multi_res_summary",
    ],
    "W3.3": [PY, "-m", "pytest", "tests/test_multi_res_drift_recovery_drill_v1.py", "-q"],
    "W4.1": [PY, "scripts/build_multi_res_fusion_bench_v1.py"],
    "W4.2": [PY, "scripts/build_theory_reflection_gap_map_v1.py"],
    "R1": [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        "scripts/verify_p0_constitution_gate_paths.ps1",
    ],
    "R3": [PY, "scripts/build_mkm_trackc_ops_dashboard_v1.py"],
}


MUST_RUN_NODES = frozenset({"W1.3", "W2.2", "W3.2", "W3.3", "R1"})


def _execute_auto_node(node: dict[str, Any]) -> tuple[str, int | None, dict[str, Any] | None]:
    node_id = node["id"]

    if node_id not in MUST_RUN_NODES and _node_done(node):
        return "done", 0, None

    if node_id in AUTO_RUNNERS:
        run = _run(AUTO_RUNNERS[node_id])
        code = int(run["exit_code"])
        if code == 0 and (node_id in MUST_RUN_NODES or _node_done(node)):
            return "done", code, run
        if code == 0:
            return "pending", code, run
        return "failed", code, run

    if node_id not in MUST_RUN_NODES and _node_done(node):
        return "done", 0, None

    return "pending", None, {"note": f"no runner wired for {node_id}"}


def run_delegation(*, dry_run: bool = False, stop_on_fail: bool = True) -> int:
    if not OUT_MAP.is_file():
        print(f"missing approval map: {OUT_MAP}", file=sys.stderr)
        return 1

    doc = _load_map()
    steps: list[dict[str, Any]] = []
    worst = 0

    for node in doc.get("nodes", []):
        approval = node.get("approval")
        if approval == "STOP":
            node["status"] = "skipped"
            continue
        if approval != "AUTO":
            continue
        if node.get("status") == "done" and _node_done(node):
            continue
        if not _deps_satisfied(doc, node):
            node["status"] = "pending"
            steps.append({"id": node["id"], "status": "blocked_deps"})
            continue

        if dry_run:
            steps.append({"id": node["id"], "status": "would_run", "evidence": node.get("evidence")})
            continue

        node["status"] = "running"
        status, exit_code, run_meta = _execute_auto_node(node)
        node["status"] = status
        node["exit_code"] = exit_code
        step = {"id": node["id"], "status": status, "exit_code": exit_code}
        if run_meta:
            step["run"] = run_meta
        steps.append(step)

        if status == "failed" or (exit_code not in (None, 0) and status != "done"):
            worst = 1
            if stop_on_fail:
                break

    done_auto = sum(
        1
        for n in doc.get("nodes", [])
        if n.get("approval") == "AUTO" and n.get("status") == "done" and _node_done(n)
    )
    total_auto = sum(1 for n in doc.get("nodes", []) if n.get("approval") == "AUTO")

    if done_auto >= total_auto and total_auto > 0:
        doc["delegation_status"] = "auto_chain_complete"
    elif done_auto > 0:
        doc["delegation_status"] = "in_progress"

    if not dry_run:
        _save_map(doc)
        subprocess.run([PY, "scripts/update_multi_res_promotion_manifest_v1.py"], cwd=str(ROOT))

    summary = {
        "schema": "multi_res_index_delegation_v1",
        "generated_at_utc": _utc_now(),
        "hypo_label": "[HYPO]",
        "research_only": True,
        "approval_map": str(OUT_MAP.relative_to(ROOT)).replace("\\", "/"),
        "auto_done": done_auto,
        "auto_total": total_auto,
        "stop_nodes_skipped": sum(1 for n in doc.get("nodes", []) if n.get("approval") == "STOP"),
        "steps": steps,
        "exit_code": worst,
    }
    OUT_SUMMARY.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return worst


def main() -> int:
    ap = argparse.ArgumentParser(description="Multi-Res Index delegation AUTO chain")
    ap.add_argument("--dry-run", action="store_true", help="List runnable AUTO nodes only")
    ap.add_argument("--no-stop-on-fail", action="store_true")
    args = ap.parse_args()
    return run_delegation(dry_run=args.dry_run, stop_on_fail=not args.no_stop_on_fail)


if __name__ == "__main__":
    raise SystemExit(main())
