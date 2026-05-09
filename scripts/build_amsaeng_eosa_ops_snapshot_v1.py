from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build Amsaeng-Eosa ops snapshot summary.")
    p.add_argument(
        "--output-json",
        default="reports/amsaeng_eosa_ops_snapshot_latest.json",
        help="Output snapshot JSON path.",
    )
    p.add_argument(
        "--output-md",
        default="reports/amsaeng_eosa_ops_snapshot_latest.md",
        help="Output snapshot markdown path.",
    )
    return p.parse_args()


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def build_snapshot(workspace: Path) -> dict[str, Any]:
    sec = _read_json(workspace / "reports" / "security_integrity_status_latest.json")
    ops = _read_json(workspace / "reports" / "athena_ops_status_latest.json")
    gate_summary = _read_json(workspace / "reports" / "execution_gate_audit_summary_latest.json")
    return {
        "schema": "amsaeng_eosa_ops_snapshot_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "automation_topology": {
            "security_check_task": "MKM-Security-Integrity-Check-5min",
            "ops_monitor_task": "MKM-Athena-Ops-Monitor-5min",
            "n8n_service_task": "MKM-n8n-Service",
            "n8n_daily_check_task": "MKM-MacroRisk-N8n-DailyCheck",
            "execution_gate_summary_task": "MKM-Execution-Gate-Audit-Summary-15min",
        },
        "current_status": {
            "security_status": sec.get("status", "UNKNOWN"),
            "ops_mode": ops.get("mode", "UNKNOWN"),
            "execution_gate_block_count": gate_summary.get("block_count", 0),
            "execution_gate_total_rows": gate_summary.get("total_rows", 0),
        },
        "artifacts": {
            "security_status": "reports/security_integrity_status_latest.json",
            "ops_status": "reports/athena_ops_status_latest.json",
            "execution_gate_audit_summary": "reports/execution_gate_audit_summary_latest.json",
            "execution_gate_audit_log": "reports/execution_gate_audit_log.jsonl",
        },
    }


def render_md(s: dict[str, Any]) -> str:
    cs = s["current_status"]
    lines = [
        "# Amsaeng-Eosa Ops Snapshot",
        "",
        f"- generated_at_utc: `{s['generated_at_utc']}`",
        f"- security_status: `{cs['security_status']}`",
        f"- ops_mode: `{cs['ops_mode']}`",
        f"- execution_gate_block_count: `{cs['execution_gate_block_count']}`",
        f"- execution_gate_total_rows: `{cs['execution_gate_total_rows']}`",
        "",
        "## Automation Tasks",
    ]
    topo = s["automation_topology"]
    for k, v in topo.items():
        lines.append(f"- `{k}`: `{v}`")
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    workspace = Path(__file__).resolve().parents[1]
    snap = build_snapshot(workspace)

    out_json = Path(args.output_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(snap, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    out_md = Path(args.output_md)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(render_md(snap), encoding="utf-8")
    print(f"amsaeng_eosa_ops_snapshot_written={out_json.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
