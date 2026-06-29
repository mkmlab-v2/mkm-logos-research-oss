#!/usr/bin/env python3
"""Guard against agent/remote session sprawl (local + optional VPS via SSH)."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports" / "agent_session_guard_latest.json"

LOCAL_AGENT_PATTERNS = ("claude", "codex")
ADVISORY_PATTERNS = ("cursor", "node", "python")
DEFAULT_MAX_AGENT = 12
DEFAULT_MAX_VPS = 20
DEFAULT_VPS_HOST = "vps-mkmlife"


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _count_local_processes() -> tuple[int, int, list[dict]]:
    if sys.platform != "win32":
        return _count_local_processes_unix()
    ps_cmd = (
        "Get-Process | Where-Object { $_.ProcessName -match "
        "'claude|codex|cursor|node|python|Code' } | "
        "Select-Object ProcessName,Id | ConvertTo-Json -Compress"
    )
    proc = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps_cmd],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if proc.returncode != 0 or not proc.stdout.strip():
        return 0, 0, []
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return 0, 0, []
    if isinstance(data, dict):
        data = [data]
    rows = [{"name": r.get("ProcessName"), "pid": r.get("Id")} for r in data if isinstance(r, dict)]
    agent_count = sum(
        1 for r in rows if str(r.get("name", "")).lower() in LOCAL_AGENT_PATTERNS or "claude" in str(r.get("name", "")).lower()
    )
    advisory_count = len(rows)
    return agent_count, advisory_count, rows[:50]


def _count_local_processes_unix() -> tuple[int, int, list[dict]]:
    proc = subprocess.run(
        ["ps", "-eo", "comm="],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    names = [ln.strip().lower() for ln in proc.stdout.splitlines() if ln.strip()]
    agent = [n for n in names if any(p in n for p in LOCAL_AGENT_PATTERNS)]
    advisory = [n for n in names if any(p in n for p in (*LOCAL_AGENT_PATTERNS, *ADVISORY_PATTERNS))]
    return len(agent), len(advisory), [{"name": n} for n in advisory[:50]]


def _count_vps_sessions(host: str) -> tuple[int | None, str | None]:
    remote = (
        "ps -eo comm= 2>/dev/null | "
        "grep -Ei 'claude|codex' | grep -v grep | wc -l"
    )
    proc = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", host, remote],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "ssh_failed").strip()
        return None, err[:300]
    try:
        return int(proc.stdout.strip()), None
    except ValueError:
        return None, "bad_wc_output"


def evaluate(
    *,
    max_agent: int,
    max_vps: int,
    vps_host: str,
    skip_vps: bool,
) -> dict:
    now = datetime.now(timezone.utc)
    agent_count, advisory_count, local_sample = _count_local_processes()
    agent_ok = agent_count <= max_agent

    vps_count: int | None = None
    vps_err: str | None = None
    vps_ok = True
    if not skip_vps and vps_host:
        vps_count, vps_err = _count_vps_sessions(vps_host)
        if vps_count is None:
            vps_ok = True  # unreachable VPS is non-fatal for guard
        else:
            vps_ok = vps_count <= max_vps

    ok = agent_ok and vps_ok
    report = {
        "schema": "agent_session_guard_v1",
        "generated_at_utc": now.isoformat(),
        "limits": {"agent_max": max_agent, "vps_max": max_vps},
        "local": {
            "agent_count": agent_count,
            "advisory_process_count": advisory_count,
            "ok": agent_ok,
            "sample": local_sample,
        },
        "vps": {
            "host": vps_host if not skip_vps else None,
            "count": vps_count,
            "ok": vps_ok,
            "error": vps_err,
            "skipped": skip_vps,
        },
        "ok": ok,
        "operator_note_ko": "153+ 원격 세션/RAM 폭주 재발 방지 — 초과 시 수동 정리, 자동 kill 없음",
    }
    if not agent_ok:
        report["reason"] = f"agent_count_exceeds_{max_agent}"
    elif vps_count is not None and not vps_ok:
        report["reason"] = f"vps_count_exceeds_{max_vps}"
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Agent session count guard")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--max-agent", type=int, default=_env_int("MKM_AGENT_SESSION_MAX", DEFAULT_MAX_AGENT))
    parser.add_argument("--max-vps", type=int, default=_env_int("MKM_AGENT_SESSION_MAX_VPS", DEFAULT_MAX_VPS))
    parser.add_argument("--vps-host", default=os.getenv("MKM_VPS_HOST", DEFAULT_VPS_HOST))
    parser.add_argument("--skip-vps", action="store_true")
    args = parser.parse_args()

    report = evaluate(
        max_agent=args.max_agent,
        max_vps=args.max_vps,
        vps_host=args.vps_host.strip(),
        skip_vps=args.skip_vps,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        f"AGENT_SESSION_GUARD ok={report['ok']} "
        f"agent={report['local']['agent_count']}/{args.max_agent} "
        f"advisory={report['local']['advisory_process_count']} "
        f"vps={report['vps']['count']}"
    )
    print(f"WROTE: {args.out}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
