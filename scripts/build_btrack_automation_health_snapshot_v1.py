from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        try:
            return json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception:
            return None


def task_query(task_name: str) -> dict[str, Any]:
    cmd = ["schtasks", "/Query", "/TN", task_name, "/V", "/FO", "LIST"]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    body = (proc.stdout or "").splitlines()
    kv: dict[str, str] = {}
    for line in body:
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        kv[k.strip()] = v.strip()
    return {
        "task_name": task_name,
        "exists": proc.returncode == 0,
        "return_code": proc.returncode,
        "last_result": kv.get("Last Result"),
        "last_run_time": kv.get("Last Run Time"),
        "next_run_time": kv.get("Next Run Time"),
        "status": kv.get("Status"),
        "task_to_run": kv.get("Task To Run"),
    }


def is_task_ok(task: dict[str, Any]) -> bool:
    if not task.get("exists"):
        return False
    if (task.get("status") or "").lower() != "ready":
        return False
    return str(task.get("last_result")) == "0"


def is_artifact_ok(preflight: dict[str, Any] | None, gate: dict[str, Any] | None, receipt: dict[str, Any] | None) -> bool:
    if preflight is None or gate is None or receipt is None:
        return False
    if (preflight.get("result") or "").upper() != "PASS":
        return False
    if (gate.get("decision") or "").lower() != "pass":
        return False
    if (receipt.get("apply_result") or "").lower() != "success":
        return False
    if bool(receipt.get("rollback_performed")):
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Build B-track automation health snapshot.")
    parser.add_argument(
        "--out",
        default="docs/final/artifacts/btrack_automation_health_snapshot_latest.json",
        help="Output JSON path",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    out_path = (root / args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    apply_receipt = read_json(root / "reports/constitution/btrack_pilot/auto_scientist/promotion_apply_receipt_latest.json")
    preflight = read_json(root / "docs/final/artifacts/promotion_preflight_v1_latest.json")
    gate = read_json(root / "reports/constitution/btrack_pilot/btrack_promotion_gate_latest.json")

    payload = {
        "schema": "btrack_automation_health_snapshot_v1",
        "generated_at_utc": utc_now_iso(),
        "tasks": {
            "auto_scientist_weekly": task_query("\\MKM_BTrack_AutoScientist_Weekly"),
            "control_tower_weekly": task_query("\\MKM_BTrack_ControlTower_Weekly"),
            "control_tower_autopush_daily": task_query("\\MKM_BTrack_ControlTower_Autopush_Daily"),
        },
        "artifacts": {
            "promotion_apply_receipt_latest": {
                "exists": apply_receipt is not None,
                "applied_at_utc": (apply_receipt or {}).get("applied_at_utc"),
                "apply_result": (apply_receipt or {}).get("apply_result"),
                "rollback_performed": (apply_receipt or {}).get("rollback_performed"),
            },
            "promotion_preflight_latest": {
                "exists": preflight is not None,
                "generated_at_utc": (preflight or {}).get("generated_at_utc"),
                "result": (preflight or {}).get("result"),
            },
            "btrack_promotion_gate_latest": {
                "exists": gate is not None,
                "generated_at_utc": (gate or {}).get("generated_at_utc"),
                "decision": (gate or {}).get("decision"),
            },
        },
    }

    tasks = payload["tasks"]
    artifacts = payload["artifacts"]
    tasks_ok = all(
        is_task_ok(tasks[k])
        for k in (
            "auto_scientist_weekly",
            "control_tower_weekly",
            "control_tower_autopush_daily",
        )
    )
    artifacts_ok = is_artifact_ok(preflight, gate, apply_receipt)
    payload["summary"] = {
        "all_tasks_ok": tasks_ok,
        "all_artifacts_ok": artifacts_ok,
        "ops_ready": tasks_ok and artifacts_ok,
    }

    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
