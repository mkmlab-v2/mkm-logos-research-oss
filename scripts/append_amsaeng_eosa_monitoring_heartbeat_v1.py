from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Append Amsaeng-Eosa monitoring heartbeat.")
    p.add_argument("--workspace-root", default="C:/workspace")
    p.add_argument("--history-jsonl", default="reports/amsaeng_eosa_monitoring_heartbeat_log.jsonl")
    p.add_argument("--latest-json", default="reports/amsaeng_eosa_monitoring_heartbeat_latest.json")
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


def main() -> int:
    args = parse_args()
    root = Path(args.workspace_root)

    sec = _read_json(root / "reports" / "security_integrity_status_latest.json")
    ops = _read_json(root / "reports" / "athena_ops_status_latest.json")
    gate = _read_json(root / "reports" / "execution_gate_audit_summary_latest.json")
    drift = _read_json(root / "reports" / "cursorrules_drift_status_latest.json")
    evidence = _read_json(root / "reports" / "fact_lock_evidence_bundle_latest.json")

    tasks = {
        "MKM-Security-Integrity-Check-5min": _task_state("MKM-Security-Integrity-Check-5min"),
        "MKM-Athena-Ops-Monitor-5min": _task_state("MKM-Athena-Ops-Monitor-5min"),
        "MKM-Execution-Gate-Audit-Summary-15min": _task_state("MKM-Execution-Gate-Audit-Summary-15min"),
        "MKM-AmsaengEosa-Monitoring-Bundle-60min": _task_state("MKM-AmsaengEosa-Monitoring-Bundle-60min"),
    }

    now = datetime.now(timezone.utc).isoformat()
    row = {
        "schema": "amsaeng_eosa_monitoring_heartbeat_v1",
        "generated_at_utc": now,
        "security_status": sec.get("status", "UNKNOWN"),
        "ops_mode": ops.get("mode", "UNKNOWN"),
        "gate_block_ratio": float(gate.get("block_ratio", 0.0) or 0.0),
        "gate_block_count": int(gate.get("block_count", 0) or 0),
        "gate_total_rows": int(gate.get("total_rows", 0) or 0),
        "cursorrules_drift_status": drift.get("status", "UNKNOWN"),
        "fact_lock_missing_count": int(evidence.get("missing_count", -1) or -1),
        "tasks": tasks,
    }

    latest = root / args.latest_json
    latest.parent.mkdir(parents=True, exist_ok=True)
    latest.write_text(json.dumps(row, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    history = root / args.history_jsonl
    history.parent.mkdir(parents=True, exist_ok=True)
    with history.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"amsaeng_eosa_monitoring_heartbeat_appended={history.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
