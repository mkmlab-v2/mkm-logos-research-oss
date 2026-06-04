#!/usr/bin/env python3
"""[HYPO] Main-side Next-Gen aux automation: deploy job → poll ports → distributed or local fallback."""
from __future__ import annotations

import argparse
import json
import socket
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHARE_DEFAULT = Path("Z:/nextgen_cpu_aux")
OUT = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_aux_automation_v1_latest.json"
)
JOB_NAME = "aux_job_request_v1.json"
RESULT_NAME = "aux_job_result_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _tcp_open(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _run(script: str, extra: list[str], timeout_s: int = 600) -> dict:
    cmd = [sys.executable, str(ROOT / script), *extra]
    try:
        proc = subprocess.run(
            cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=timeout_s
        )
        return {"exit_code": proc.returncode, "timed_out": False}
    except subprocess.TimeoutExpired:
        return {"exit_code": 124, "timed_out": True}


def _write_job(share: Path, action: str) -> str:
    rid = uuid.uuid4().hex[:12]
    job = {
        "schema": "nextgen_aux_job_request_v1",
        "request_id": rid,
        "requested_at_utc": _utc(),
        "research_only": True,
        "action": action,
    }
    share.mkdir(parents=True, exist_ok=True)
    (share / JOB_NAME).write_text(
        json.dumps(job, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return rid


def _trigger_remote_watchdog(aux_host: str, task_name: str) -> dict:
    cmd = ["schtasks", "/Run", "/S", aux_host, "/TN", task_name]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=8)
        return {
            "command": " ".join(cmd),
            "exit_code": proc.returncode,
            "stdout": (proc.stdout or "").strip()[-200:],
            "stderr": (proc.stderr or "").strip()[-200:],
        }
    except subprocess.TimeoutExpired:
        return {"command": " ".join(cmd), "exit_code": 124, "timed_out": True}


def _remote_task_exists(aux_host: str, task_name: str) -> bool:
    try:
        proc = subprocess.run(
            ["schtasks", "/Query", "/S", aux_host, "/TN", task_name],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return proc.returncode == 0
    except subprocess.TimeoutExpired:
        return False


def _poll_ports(aux_ip: str, need_p1: bool, wait_sec: int, interval: float) -> dict:
    deadline = time.monotonic() + wait_sec
    last = {"rtt_19876": False, "p1_19877": False}
    while time.monotonic() < deadline:
        last = {
            "rtt_19876": _tcp_open(aux_ip, 19876),
            "p1_19877": _tcp_open(aux_ip, 19877),
        }
        if last["rtt_19876"] and (last["p1_19877"] or not need_p1):
            break
        time.sleep(interval)
    last["ready"] = last["rtt_19876"] and (last["p1_19877"] or not need_p1)
    last["waited_sec"] = wait_sec
    return last


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--aux-ip", default="180.224.2.24")
    ap.add_argument("--aux-host", default="DESKTOP-AP1DC83")
    ap.add_argument("--share-root", type=Path, default=SHARE_DEFAULT)
    ap.add_argument("--wait-sec", type=int, default=90)
    ap.add_argument("--action", default="start_all_and_shard")
    ap.add_argument("--remote-task", default="MKM_NextGen_AuxWatchdog")
    ap.add_argument("--skip-deploy", action="store_true")
    ap.add_argument("--skip-remote-trigger", action="store_true")
    ap.add_argument("--fallback-local", action="store_true", default=True)
    ap.add_argument("--no-fallback-local", action="store_false", dest="fallback_local")
    ap.add_argument(
        "--main-only",
        action="store_true",
        help="Skip aux entirely: no Z: job, port wait, or remote trigger; local 2-shard only",
    )
    ap.add_argument("--out-json", type=Path, default=OUT)
    args = ap.parse_args()

    if args.main_only:
        doc = {
            "schema": "ng40_aux_automation_v1",
            "generated_at_utc": _utc(),
            "research_only": True,
            "main_only": True,
            "aux_excluded": True,
            "mode": "main_only_local_both_shards",
            "verdict": "aux_pc_excluded_by_operator",
            "steps": [
                _run(
                    "scripts/run_nextgen_ng40_golden40_distributed_chain_v1.py",
                    ["--local-both-shards"],
                    900,
                )
            ],
        }
        doc["chain_exit_code"] = int(doc["steps"][0].get("exit_code") or 0)
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(
            json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(
            json.dumps(
                {
                    "wrote": str(args.out_json),
                    "mode": doc["mode"],
                    "aux_excluded": True,
                },
                ensure_ascii=False,
            )
        )
        return doc["chain_exit_code"]

    share = args.share_root
    doc: dict = {
        "schema": "ng40_aux_automation_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "aux_ip": args.aux_ip,
        "aux_host": args.aux_host,
        "share_root": str(share),
        "steps": [],
    }

    if not share.parent.exists():
        doc["verdict"] = "share_not_mounted"
        doc["operator_next"] = ["Mount Z:\\ to DESKTOP-AP1DC83\\share"]
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(doc, ensure_ascii=False))
        return 1

    if not args.skip_deploy:
        doc["steps"].append(
            _run(
                "scripts/deploy_nextgen_clean_slate_cpu_aux_drop_v1.py",
                ["--share-root", str(share), "--merge-only"],
                120,
            )
        )

    rid = _write_job(share, args.action)
    doc["job_request_id"] = rid

    if not args.skip_remote_trigger and _remote_task_exists(args.aux_host, args.remote_task):
        doc["remote_trigger"] = _trigger_remote_watchdog(args.aux_host, args.remote_task)
    else:
        doc["remote_trigger"] = {
            "skipped": True,
            "reason": "remote task missing or --skip-remote-trigger",
            "one_time_setup": (
                f"On aux PC (admin): powershell -File C:\\workspace\\scripts\\"
                f"Register-NextGenAuxWatchdogTask.ps1"
            ),
        }

    doc["port_poll"] = _poll_ports(args.aux_ip, need_p1=True, wait_sec=args.wait_sec, interval=2.0)

    true_aux_ready = doc["port_poll"].get("p1_19877") and (share / RESULT_NAME).is_file()
    shard1 = share / "ng40_golden40_shard1_v1_latest.json"
    if shard1.is_file() and (share / "ng40_shard1_publish_from_main_v1.json").is_file():
        true_aux_ready = False
        doc["note"] = "shard1 on share is publish-from-main copy; not aux compute"

    chain_rc = 0
    if doc["port_poll"].get("p1_19877"):
        doc["steps"].append(
            _run("scripts/run_nextgen_ng40_golden40_distributed_chain_v1.py", [], 900)
        )
        chain_rc = int(doc["steps"][-1].get("exit_code") or 0)
        doc["mode"] = "true_aux_distributed"
    elif args.fallback_local:
        doc["steps"].append(
            _run(
                "scripts/run_nextgen_ng40_golden40_distributed_chain_v1.py",
                ["--local-both-shards"],
                900,
            )
        )
        chain_rc = int(doc["steps"][-1].get("exit_code") or 0)
        doc["mode"] = "fallback_local_both_shards"
        doc["verdict"] = "aux_unreachable_used_local_fallback"
    else:
        doc["mode"] = "failed_no_fallback"
        doc["verdict"] = "aux_p1_closed"
        chain_rc = 1

    if (share / RESULT_NAME).is_file():
        try:
            doc["aux_result"] = json.loads((share / RESULT_NAME).read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError:
            doc["aux_result"] = None

    doc["chain_exit_code"] = chain_rc
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "wrote": str(args.out_json),
                "mode": doc.get("mode"),
                "verdict": doc.get("verdict"),
                "p1_19877": doc["port_poll"].get("p1_19877"),
            },
            ensure_ascii=False,
        )
    )
    return chain_rc


if __name__ == "__main__":
    raise SystemExit(main())
