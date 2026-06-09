#!/usr/bin/env python3
"""Parallel passive loop v1 — 4-lane AUTO delegation (shim · L1 canary · MAX_HYPO · web_ops).

research_only · Track A / live / apply-active / MISSION_LOG write forbidden from this script.
SSOT summary: reports/parallel_passive_loop_v1_latest.json
Approval map: reports/delegation_parallel_passive_loop_approval_map_v1_latest.json
"""
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
OUT_SUMMARY = ROOT / "reports/parallel_passive_loop_v1_latest.json"
OUT_MAP = ROOT / "reports/delegation_parallel_passive_loop_approval_map_v1_latest.json"
KOSPI_CSV = ROOT / "research/market_data/kospi_daily_external_yf.csv"
MAX_HYPO_SHADOW = (
    ROOT / "experiments/max_hypo_unbound/results/max_hypo_t10_shadow_eval_v1_latest.json"
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


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _kospi_latest_date() -> str | None:
    if not KOSPI_CSV.is_file():
        return None
    last: str | None = None
    with KOSPI_CSV.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            d = (row.get("Date") or "").strip()
            if d:
                last = d
    return last


def _max_hypo_gate() -> tuple[bool, str]:
    latest = _kospi_latest_date()
    if not latest:
        return False, "kospi_csv_missing"
    shadow = _read_json(MAX_HYPO_SHADOW) or {}
    shadow_dates = {
        s.get("session_date")
        for s in (shadow.get("spotlight_sessions") or [])
        if isinstance(s, dict)
    }
    if latest in shadow_dates:
        return False, f"already_scored:{latest}"
    return True, f"new_session:{latest}"


def _cdp_up(url: str = "http://127.0.0.1:9222/json/version") -> bool:
    try:
        with urlopen(url, timeout=3) as resp:
            return resp.status == 200
    except OSError:
        return False


def lane_shim() -> dict[str, Any]:
    ps1 = ROOT / "scripts/Invoke-ChatShimMaintenanceRoutine_v1.ps1"
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
    bench = _read_json(ROOT / "reports/chat_shim_compress_ab_bench_v1_latest.json") or {}
    shadow = _read_json(ROOT / "reports/chat_shim_upstream_shadow_v1_latest.json") or {}
    plan = _read_json(ROOT / "reports/local_cursor_chat_shim_plan_v1_latest.json") or {}
    saving = bench.get("bundle_token_saving_rate")
    if saving is None:
        saving = (bench.get("aggregate") or {}).get("bundle_token_saving_rate")
    status = "done" if r["exit_code"] == 0 else "failed"
    return {
        "id": "A",
        "name": "chat_shim_maintenance",
        "approval": "AUTO",
        "status": status,
        "exit_code": r["exit_code"],
        "evidence": "reports/chat_shim_compress_ab_bench_v1_latest.json",
        "facts": {
            "bundle_token_saving_rate": saving,
            "shadow_pass": shadow.get("shadow_pass"),
            "ready_for_upstream_live": plan.get("ready_for_upstream_live"),
        },
        "run": r,
    }


def lane_l1_canary() -> dict[str, Any]:
    daily = _run([sys.executable, str(ROOT / "scripts/run_l1_inverse_decoder_daily_gate_v1.py")])
    guard_ps1 = ROOT / "scripts/run_l1_inverse_decoder_mode_router_v3_canary_guard.ps1"
    guard = (
        _run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(guard_ps1),
            ]
        )
        if guard_ps1.is_file()
        else {"exit_code": 0, "skipped": True}
    )
    exit_code = daily["exit_code"] if guard.get("exit_code", 0) == 0 else guard["exit_code"]
    gate = _read_json(ROOT / "docs/final/artifacts/l1_inverse_decoder_daily_gate_v1_latest.json") or {}
    canary = (
        _read_json(
            ROOT / "docs/final/artifacts/l1_inverse_decoder_mode_router_v3_canary_status_latest.json"
        )
        or {}
    )
    gate_block = gate.get("gate") or {}
    status = "done" if exit_code == 0 else "failed"
    return {
        "id": "B",
        "name": "l1_canary_observation",
        "approval": "AUTO",
        "status": status,
        "exit_code": exit_code,
        "evidence": "docs/final/artifacts/l1_inverse_decoder_daily_gate_v1_latest.json",
        "facts": {
            "daily_gate_decision": gate_block.get("decision"),
            "canary_phase": (canary or {}).get("phase"),
            "traffic_pct": (canary or {}).get("traffic_pct"),
            "canary_action": ((canary or {}).get("decision") or {}).get("action"),
        },
        "run": {"daily": daily, "guard": guard},
    }


def lane_max_hypo() -> dict[str, Any]:
    should_run, reason = _max_hypo_gate()
    latest = _kospi_latest_date()
    if not should_run:
        return {
            "id": "C",
            "name": "max_hypo_t10_shadow",
            "approval": "AUTO",
            "status": "skipped",
            "exit_code": 0,
            "skip_reason": reason,
            "evidence": str(MAX_HYPO_SHADOW.relative_to(ROOT)).replace("\\", "/"),
            "facts": {"kospi_latest_date": latest},
        }
    script = ROOT / "scripts/sandbox/run_max_hypo_t10_shadow_eval_v1.py"
    r = _run(
        [
            sys.executable,
            str(script),
            "--include-latest-kospi-day",
        ]
    )
    shadow = _read_json(MAX_HYPO_SHADOW) or {}
    delta = shadow.get("full_delta_pp")
    if delta is None:
        delta = shadow.get("shadow_delta_pp")
    status = "done" if r["exit_code"] == 0 else "failed"
    return {
        "id": "C",
        "name": "max_hypo_t10_shadow",
        "approval": "AUTO",
        "status": status,
        "exit_code": r["exit_code"],
        "evidence": str(MAX_HYPO_SHADOW.relative_to(ROOT)).replace("\\", "/"),
        "facts": {
            "kospi_latest_date": latest,
            "full_delta_pp": delta,
        },
        "run": r,
    }


def lane_web_ops(*, skip_live_cdp: bool) -> dict[str, Any]:
    cmd = [
        sys.executable,
        str(ROOT / "scripts/run_mkm_ops_memory_web_ops_fusion_v1.py"),
        "--parallel-post-overlay",
        "--include-slice",
    ]
    if skip_live_cdp:
        cmd.append("--skip-live-cdp")
    r = _run(cmd)
    gate = _read_json(ROOT / "reports/web_ops_regime_gate_v1_latest.json") or {}
    bench = _read_json(ROOT / "reports/mkm_ops_memory_web_ops_retrieval_bench_v1_latest.json") or {}
    coord = bench.get("coordinate_v1") or {}
    status = "done" if r["exit_code"] == 0 else "failed"
    return {
        "id": "D",
        "name": "web_ops_fusion",
        "approval": "AUTO",
        "status": status,
        "exit_code": r["exit_code"],
        "evidence": "reports/web_ops_regime_gate_v1_latest.json",
        "facts": {
            "gate_pass": gate.get("gate_pass"),
            "cdp_live_attempted": not skip_live_cdp,
            "coordinate_mean_tokens": coord.get("mean_tokens_per_scenario"),
        },
        "run": r,
    }


def _build_approval_map(nodes: list[dict[str, Any]], *, loop_ok: bool) -> dict[str, Any]:
    return {
        "schema": "delegation_parallel_passive_loop_approval_map_v1",
        "generated_at_utc": _utc_now(),
        "project_id": "parallel_passive_loop_v1",
        "hypo_label": "[HYPO]",
        "research_only": True,
        "track_a_active_write": False,
        "delegation_status": "auto_complete" if loop_ok else "partial_fail",
        "ssot": {
            "mission_log_section": "MISSION_LOG.md §병렬 패시브 루프",
            "runner": "scripts/run_parallel_passive_loop_v1.py",
            "persona": "Invoke-MkmPersonaHealth_v1.ps1 -Persona ParallelPassiveLoop",
            "resume_trigger": "@MISSION_LOG.md 미션로그 이어서 — 병렬 패시브",
        },
        "global_stop_rules": [
            "apply-active without human sign-off",
            "live trading ON / trading_go_no_go override",
            "MISSION_LOG concurrent write from multiple chats",
            "oracle headline merge from MAX_HYPO",
            "MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json write",
            "nebius web_ops fusion until GPU approval (default STOP lane D)",
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


def _skipped_web_ops_node(*, reason: str) -> dict[str, Any]:
    return {
        "id": "D",
        "name": "web_ops_fusion",
        "approval": "STOP",
        "status": "skipped",
        "exit_code": 0,
        "skip_reason": reason,
        "evidence": "reports/web_ops_regime_gate_v1_latest.json",
        "facts": {"nebius_touched": False},
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Parallel passive loop v1 (3 lanes default; Nebius STOP)")
    ap.add_argument("--dry-run", action="store_true", help="Plan only; no subprocess")
    ap.add_argument("--sequential", action="store_true", help="Run lanes one-by-one (debug)")
    ap.add_argument("--skip-shim", action="store_true")
    ap.add_argument("--skip-l1", action="store_true")
    ap.add_argument("--skip-max-hypo", action="store_true")
    ap.add_argument(
        "--include-web-ops",
        action="store_true",
        help="GPU 승인 후에만: lane D (Nebius/CDP web_ops fusion) 실행",
    )
    ap.add_argument(
        "--skip-web-ops",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    ap.add_argument("--skip-live-cdp", action="store_true", help="web_ops 시 CDP capture 생략")
    args = ap.parse_args()

    # Default: Nebius/web_ops OFF until commander GPU approval (--include-web-ops).
    skip_web_ops = args.skip_web_ops or not args.include_web_ops
    skip_cdp = args.skip_live_cdp or not _cdp_up()
    plan: list[tuple[str, Any]] = []
    if not args.skip_shim:
        plan.append(("shim", lane_shim))
    if not args.skip_l1:
        plan.append(("l1", lane_l1_canary))
    if not args.skip_max_hypo:
        plan.append(("max_hypo", lane_max_hypo))
    if not skip_web_ops:
        plan.append(("web_ops", lambda: lane_web_ops(skip_live_cdp=skip_cdp)))

    if args.dry_run:
        payload = {
            "schema": "parallel_passive_loop_v1",
            "generated_at_utc": _utc_now(),
            "dry_run": True,
            "lanes_planned": [p[0] for p in plan],
            "cdp_up": _cdp_up(),
            "kospi_latest": _kospi_latest_date(),
            "max_hypo_gate": _max_hypo_gate(),
        }
        OUT_SUMMARY.parent.mkdir(parents=True, exist_ok=True)
        OUT_SUMMARY.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0

    nodes: list[dict[str, Any]] = []

    def _exec(item: tuple[str, Any]) -> dict[str, Any]:
        _key, fn = item
        if _key == "web_ops":
            return fn()
        return fn()

    if args.sequential:
        for item in plan:
            nodes.append(_exec(item))
    else:
        with ThreadPoolExecutor(max_workers=min(4, len(plan) or 1)) as pool:
            futures = {pool.submit(_exec, item): item[0] for item in plan}
            by_name: dict[str, dict[str, Any]] = {}
            for fut in as_completed(futures):
                by_name[futures[fut]] = fut.result()
            for key, _ in plan:
                nodes.append(by_name[key])

    if skip_web_ops:
        nodes.append(_skipped_web_ops_node(reason="gpu_approval_hold_nebius_no_touch"))

    hard_fail = any(n["status"] == "failed" for n in nodes)
    loop_ok = not hard_fail
    summary = {
        "schema": "parallel_passive_loop_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "track_a_active_write": False,
        "loop_ok": loop_ok,
        "nebius_lane_default": "STOP_until_gpu_approval",
        "web_ops_included": not skip_web_ops,
        "cdp_up": _cdp_up() if not skip_web_ops else None,
        "lanes": nodes,
    }
    approval = _build_approval_map(nodes, loop_ok=loop_ok)

    OUT_SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    OUT_SUMMARY.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    OUT_MAP.write_text(json.dumps(approval, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(json.dumps({"ok": loop_ok, "out": str(OUT_SUMMARY.relative_to(ROOT))}, ensure_ascii=False))
    return 1 if hard_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
