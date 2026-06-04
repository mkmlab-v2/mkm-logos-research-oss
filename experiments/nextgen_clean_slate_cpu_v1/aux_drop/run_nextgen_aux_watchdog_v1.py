#!/usr/bin/env python3
"""[HYPO] Aux PC watchdog: poll Z:\\nextgen_cpu_aux job file and run servers / NG40 shard."""
from __future__ import annotations

import argparse
import json
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_SHARE = Path("Z:/nextgen_cpu_aux")
WORKSPACE = Path("C:/workspace")
JOB_NAME = "aux_job_request_v1.json"
RESULT_NAME = "aux_job_result_v1_latest.json"
PROCESSED_PREFIX = "aux_job_request_processed_"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _tcp_open(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _port_listening_local(port: int) -> bool:
    return _tcp_open("127.0.0.1", port)


def _popen_server(share: Path, script: str, port: int) -> dict:
    if _port_listening_local(port):
        return {"script": script, "port": port, "status": "already_listening"}
    py = sys.executable
    cmd = [py, str(share / script), "--port", str(port)]
    flags = 0
    if sys.platform == "win32":
        flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    subprocess.Popen(
        cmd,
        cwd=str(share),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=flags,
    )
    time.sleep(0.8)
    return {
        "script": script,
        "port": port,
        "status": "started" if _port_listening_local(port) else "start_unconfirmed",
    }


def _start_servers(share: Path) -> list[dict]:
    return [
        _popen_server(share, "run_rtt_server_standalone.py", 19876),
        _popen_server(share, "run_p1_server_standalone.py", 19877),
    ]


def _run_ng40_shard1(share: Path) -> dict:
    out_json = share / "ng40_golden40_shard1_v1_latest.json"
    stamp = share / "ng40_shard1_publish_from_main_v1.json"
    if stamp.is_file():
        try:
            stamp.unlink()
        except OSError:
            pass
    script = WORKSPACE / "scripts/run_nextgen_ng40_golden40_shard_eval_v1.py"
    if not script.is_file():
        return {
            "status": "fail",
            "reason": "C:\\workspace clone missing on aux",
            "hint": "Clone repo to C:\\workspace on DESKTOP-AP1DC83",
        }
    cmd = [
        sys.executable,
        str(script),
        "--shard-index",
        "1",
        "--shard-count",
        "2",
        "--match-active-caps",
        "--out-json",
        str(out_json),
    ]
    proc = subprocess.run(cmd, cwd=str(WORKSPACE), capture_output=True, text=True, timeout=900)
    return {
        "status": "ok" if proc.returncode == 0 else "fail",
        "exit_code": proc.returncode,
        "out_json": str(out_json),
        "stdout_tail": (proc.stdout or "")[-400:],
        "stderr_tail": (proc.stderr or "")[-200:],
    }


def _process_job(share: Path, job: dict) -> dict:
    action = str(job.get("action") or "")
    result: dict = {"action": action, "processed_at_utc": _utc(), "research_only": True}
    if action in ("start_servers", "start_all", "start_all_and_shard"):
        result["servers"] = _start_servers(share)
        result["ports"] = {"rtt_19876": _port_listening_local(19876), "p1_19877": _port_listening_local(19877)}
    if action in ("run_ng40_shard1", "start_all_and_shard"):
        result["ng40_shard1"] = _run_ng40_shard1(share)
    if not action:
        result["status"] = "fail"
        result["reason"] = "missing action"
    else:
        result["status"] = "ok"
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--share-root", type=Path, default=DEFAULT_SHARE)
    ap.add_argument("--once", action="store_true", help="Process at most one pending job and exit")
    ap.add_argument("--poll-sec", type=float, default=2.0)
    ap.add_argument("--max-wait-sec", type=float, default=0.0, help=">0: loop until job or timeout")
    args = ap.parse_args()

    share = args.share_root
    job_path = share / JOB_NAME
    if not share.is_dir():
        print(json.dumps({"error": "share_missing", "share": str(share)}, ensure_ascii=False))
        return 1

    def _tick() -> int:
        if not job_path.is_file():
            return 0
        job = json.loads(job_path.read_text(encoding="utf-8-sig"))
        rid = str(job.get("request_id") or "unknown")
        processed_marker = share / f"{PROCESSED_PREFIX}{rid}.json"
        if processed_marker.is_file():
            return 0
        result = _process_job(share, job)
        result["request_id"] = rid
        (share / RESULT_NAME).write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        processed_marker.write_text(json.dumps(job, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        try:
            job_path.unlink()
        except OSError:
            pass
        print(json.dumps({"processed": rid, "status": result.get("status")}, ensure_ascii=False))
        return 0

    if args.max_wait_sec <= 0:
        return _tick()

    deadline = time.monotonic() + args.max_wait_sec
    while time.monotonic() < deadline:
        if job_path.is_file():
            return _tick()
        time.sleep(args.poll_sec)
    print(json.dumps({"status": "no_job", "waited_sec": args.max_wait_sec}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
