from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build weekly audit packet for Amsaeng-Eosa automation.")
    p.add_argument("--workspace-root", default="C:/workspace")
    p.add_argument("--output-json", default="reports/amsaeng_eosa_weekly_audit_packet_latest.json")
    p.add_argument("--output-md", default="reports/amsaeng_eosa_weekly_audit_packet_latest.md")
    return p.parse_args()


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _task_state(name: str) -> str:
    import subprocess

    cmd = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        f"(Get-ScheduledTask -TaskName '{name}' -ErrorAction SilentlyContinue | Select-Object -ExpandProperty State)",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        return "UNKNOWN"
    s = (proc.stdout or "").strip()
    return s or "MISSING"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
            if isinstance(row, dict):
                rows.append(row)
        except json.JSONDecodeError:
            continue
    return rows


def _safe_parse_iso(dt_text: str) -> datetime | None:
    try:
        return datetime.fromisoformat(dt_text.replace("Z", "+00:00"))
    except ValueError:
        return None


def main() -> int:
    args = parse_args()
    root = Path(args.workspace_root)
    sec = _read_json(root / "reports" / "security_integrity_status_latest.json")
    ops = _read_json(root / "reports" / "athena_ops_status_latest.json")
    gate = _read_json(root / "reports" / "execution_gate_audit_summary_latest.json")
    drift = _read_json(root / "reports" / "cursorrules_drift_status_latest.json")
    evidence = _read_json(root / "reports" / "fact_lock_evidence_bundle_latest.json")
    history_rows = _read_jsonl(root / "reports" / "amsaeng_eosa_monitoring_heartbeat_log.jsonl")
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(days=7)
    recent_rows = []
    for row in history_rows:
        ts = _safe_parse_iso(str(row.get("generated_at_utc", "")))
        if ts is not None and ts >= window_start:
            recent_rows.append(row)

    recent_count = len(recent_rows)
    gate_avg = (
        sum(float(r.get("gate_block_ratio", 0.0) or 0.0) for r in recent_rows) / recent_count
        if recent_count
        else 0.0
    )
    security_red_count = sum(1 for r in recent_rows if str(r.get("security_status", "")).upper() == "RED")
    ops_safe_count = sum(1 for r in recent_rows if str(r.get("ops_mode", "")).upper() == "SAFE")
    drift_count = sum(
        1 for r in recent_rows if str(r.get("cursorrules_drift_status", "")).upper() not in {"PASS", "IN_SYNC"}
    )

    task_issue_counts = {
        "MKM-Security-Integrity-Check-5min": 0,
        "MKM-Athena-Ops-Monitor-5min": 0,
        "MKM-Execution-Gate-Audit-Summary-15min": 0,
        "MKM-AmsaengEosa-Monitoring-Bundle-60min": 0,
    }
    for row in recent_rows:
        t = row.get("tasks", {})
        if not isinstance(t, dict):
            continue
        for key in list(task_issue_counts.keys()):
            state = str(t.get(key, "UNKNOWN")).upper()
            if state not in {"READY", "RUNNING"}:
                task_issue_counts[key] += 1

    tasks = {
        "MKM-Security-Integrity-Check-5min": _task_state("MKM-Security-Integrity-Check-5min"),
        "MKM-Athena-Ops-Monitor-5min": _task_state("MKM-Athena-Ops-Monitor-5min"),
        "MKM-Execution-Gate-Audit-Summary-15min": _task_state("MKM-Execution-Gate-Audit-Summary-15min"),
        "MKM-AmsaengEosa-Monitoring-Bundle-60min": _task_state("MKM-AmsaengEosa-Monitoring-Bundle-60min"),
    }

    packet = {
        "schema": "amsaeng_eosa_weekly_audit_packet_v1",
        "generated_at_utc": now.isoformat(),
        "security_status": sec.get("status", "UNKNOWN"),
        "ops_mode": ops.get("mode", "UNKNOWN"),
        "execution_gate_block_count": gate.get("block_count", 0),
        "execution_gate_total_rows": gate.get("total_rows", 0),
        "cursorrules_drift_status": drift.get("status", "UNKNOWN"),
        "fact_lock_missing_count": evidence.get("missing_count", -1),
        "weekly_window": {
            "days": 7,
            "sample_count": recent_count,
            "gate_block_ratio_avg": round(gate_avg, 6),
            "security_red_count": security_red_count,
            "ops_safe_count": ops_safe_count,
            "cursorrules_drift_count": drift_count,
            "task_non_ready_counts": task_issue_counts,
        },
        "tasks": tasks,
    }

    out_json = root / args.output_json
    out_md = root / args.output_md
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md = [
        "# Amsaeng-Eosa Weekly Audit Packet",
        "",
        f"- generated_at_utc: `{packet['generated_at_utc']}`",
        f"- security_status: `{packet['security_status']}`",
        f"- ops_mode: `{packet['ops_mode']}`",
        f"- execution_gate_block_count: `{packet['execution_gate_block_count']}`",
        f"- execution_gate_total_rows: `{packet['execution_gate_total_rows']}`",
        f"- cursorrules_drift_status: `{packet['cursorrules_drift_status']}`",
        f"- fact_lock_missing_count: `{packet['fact_lock_missing_count']}`",
        "",
        "## Weekly Window (7d)",
        f"- sample_count: `{packet['weekly_window']['sample_count']}`",
        f"- gate_block_ratio_avg: `{packet['weekly_window']['gate_block_ratio_avg']}`",
        f"- security_red_count: `{packet['weekly_window']['security_red_count']}`",
        f"- ops_safe_count: `{packet['weekly_window']['ops_safe_count']}`",
        f"- cursorrules_drift_count: `{packet['weekly_window']['cursorrules_drift_count']}`",
        "",
        "## Task States",
    ]
    for k, v in tasks.items():
        md.append(f"- `{k}`: `{v}`")
    md.append("")
    md.append("## Weekly Task Non-Ready Counts")
    for k, v in packet["weekly_window"]["task_non_ready_counts"].items():
        md.append(f"- `{k}`: `{v}`")
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"amsaeng_eosa_weekly_audit_packet_written={out_json.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
