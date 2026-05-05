#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Print a one-screen B-track Auto Scientist / control tower ops brief (stdout).

Reads the same artifact bundle as ``build_btrack_automation_health_snapshot_v1.py``.
Windows scheduled-task rows are included only on ``win32`` (``schtasks``).
Exit 0 after printing; stderr only for unexpected errors.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


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
        "last_result": kv.get("Last Result"),
        "last_run_time": kv.get("Last Run Time"),
        "next_run_time": kv.get("Next Run Time"),
        "status": kv.get("Status"),
    }


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    receipt_path = root / "reports/constitution/btrack_pilot/auto_scientist/promotion_apply_receipt_latest.json"
    preflight_path = root / "docs/final/artifacts/promotion_preflight_v1_latest.json"
    gate_path = root / "reports/constitution/btrack_pilot/btrack_promotion_gate_latest.json"

    receipt = read_json(receipt_path)
    preflight = read_json(preflight_path)
    gate = read_json(gate_path)

    lines: list[str] = []
    lines.append("=== B-track Auto Scientist / control tower — brief ===")
    lines.append("")

    lines.append("--- Artifacts ---")
    if receipt:
        lines.append(
            f"  promotion_apply_receipt: apply_result={receipt.get('apply_result')!r} "
            f"readiness={receipt.get('promotion_readiness')!r} "
            f"applied_at_utc={receipt.get('applied_at_utc')!r} "
            f"rollback={receipt.get('rollback_performed')!r}"
        )
    else:
        lines.append("  promotion_apply_receipt: (missing) " + str(receipt_path))

    if preflight:
        lines.append(
            f"  preflight: result={preflight.get('result')!r} "
            f"generated_at_utc={preflight.get('generated_at_utc')!r}"
        )
    else:
        lines.append("  preflight: (missing) " + str(preflight_path))

    if gate:
        lines.append(
            f"  promotion_gate: decision={gate.get('decision')!r} "
            f"generated_at_utc={gate.get('generated_at_utc')!r}"
        )
    else:
        lines.append("  promotion_gate: (missing) " + str(gate_path))

    lines.append("")

    if sys.platform == "win32":
        lines.append("--- Scheduled tasks (Windows) ---")
        for name in (
            "\\MKM_BTrack_AutoScientist_Weekly",
            "\\MKM_BTrack_ControlTower_Weekly",
            "\\MKM_BTrack_ControlTower_Autopush_Daily",
        ):
            t = task_query(name)
            if t.get("exists"):
                lines.append(
                    f"  {name}: status={t.get('status')!r} last_result={t.get('last_result')!r} "
                    f"last_run={t.get('last_run_time')!r}"
                )
            else:
                lines.append(f"  {name}: (not found or query failed)")
        lines.append("")
    else:
        lines.append("--- Scheduled tasks: skipped (not win32) ---")
        lines.append("")

    lines.append(
        "Paths: receipt → promotion_apply_receipt_latest.json | "
        "preflight → promotion_preflight_v1_latest.json | "
        "gate → btrack_promotion_gate_latest.json"
    )

    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
