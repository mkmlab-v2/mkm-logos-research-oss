#!/usr/bin/env python3
"""Guardrail upgrade autopilot v1 — research_only plan from radar + safe_ops inputs.

Writes docs/final/artifacts/guardrail_upgrade_autopilot_latest.json.
Does not execute recovery chains or promote Track A.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "guardrail_upgrade_autopilot_latest.json"
RADAR_PATH = ROOT / "docs" / "final" / "artifacts" / "open_source_tech_radar_latest.json"
SAFE_OPS_PATH = ROOT / "reports" / "safe_ops_surface_check_latest.json"
TRADING_HEALTH_PATH = ROOT / "reports" / "trading_automation_health_latest.json"
BUILD_REPORT = ROOT / "reports" / "guardrail_upgrade_autopilot_build_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return None


def _upgrade_target_names(radar: dict[str, Any] | None) -> list[str]:
    if not radar:
        return []
    names: list[str] = []
    for row in radar.get("upgrade_targets") or []:
        if isinstance(row, dict) and row.get("name"):
            names.append(str(row["name"]))
    return names


def _classify_safe_ops(safe_ops: dict[str, Any] | None) -> dict[str, int]:
    counts = {"policy": 0, "artifact": 0, "runtime": 0}
    if not safe_ops:
        counts["artifact"] += 1
        return counts
    status = str(safe_ops.get("status") or "").lower()
    messages = safe_ops.get("messages") or {}
    critical = messages.get("critical") or []
    warning = messages.get("warning") or []
    if critical:
        counts["runtime"] += len(critical)
    if warning:
        counts["runtime"] += len(warning)
    if status in {"critical", "fail"}:
        counts["runtime"] += 1
    if safe_ops.get("verify_trading_automation_exit_code") not in (0, None):
        counts["policy"] += 1
    return counts


def build_autopilot(
    *,
    radar: dict[str, Any] | None,
    safe_ops: dict[str, Any] | None,
    trading_health: dict[str, Any] | None,
) -> dict[str, Any]:
    failure_classification = _classify_safe_ops(safe_ops)
    runtime_failures = failure_classification["runtime"]
    autopilot_state = "ready"
    if runtime_failures > 0:
        autopilot_state = "degraded"
    if failure_classification["artifact"] > 0 and not radar:
        autopilot_state = "blocked"

    queue: list[dict[str, str]] = [
        {
            "id": "guardrail_check_p0",
            "class": "runtime",
            "command": "powershell -NoProfile -ExecutionPolicy Bypass -File scripts/verify_p0_constitution_gate_paths.ps1",
            "why": "Ensure paths are present before any recovery chain.",
        }
    ]
    if safe_ops and str(safe_ops.get("status") or "").lower() in {"degraded", "critical", "fail"}:
        queue.append(
            {
                "id": "safe_ops_surface_recheck",
                "class": "runtime",
                "command": "powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-SafeOpsSurfaceCheck.ps1",
                "why": "Refresh safe_ops_surface_check_latest.json after staleness or verify warnings.",
            }
        )
    if radar and radar.get("build_mode") == "offline_refresh":
        queue.append(
            {
                "id": "oss_tech_radar_fetch_optional",
                "class": "artifact",
                "command": "py scripts/build_open_source_tech_radar_v1.py --fetch",
                "why": "Optional network refresh when offline_refresh is stale; B-track only.",
            }
        )

    return {
        "schema_version": "guardrail_upgrade_autopilot_v1",
        "generated_at_utc": _utc_now(),
        "inputs": {
            "radar_present": radar is not None,
            "radar_build_mode": (radar or {}).get("build_mode"),
            "safe_ops_present": safe_ops is not None,
            "safe_ops_status": (safe_ops or {}).get("status"),
            "trading_health_present": trading_health is not None,
        },
        "top_upgrade_targets": _upgrade_target_names(radar)[:8],
        "failure_classification": failure_classification,
        "execution_queue": queue,
        "autopilot_state": autopilot_state,
        "disclaimer": "research_only",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--radar-json", type=Path, default=RADAR_PATH)
    ap.add_argument("--safe-ops-json", type=Path, default=SAFE_OPS_PATH)
    ap.add_argument("--trading-health-json", type=Path, default=TRADING_HEALTH_PATH)
    args = ap.parse_args()

    doc = build_autopilot(
        radar=_read_json(args.radar_json),
        safe_ops=_read_json(args.safe_ops_json),
        trading_health=_read_json(args.trading_health_json),
    )
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(
        json.dumps(doc, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    try:
        out_rel = str(args.out_json.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        out_rel = str(args.out_json).replace("\\", "/")
    report = {
        "schema": "guardrail_upgrade_autopilot_build_v1",
        "generated_at_utc": doc["generated_at_utc"],
        "out_json": out_rel,
        "autopilot_state": doc["autopilot_state"],
        "queue_len": len(doc["execution_queue"]),
        "reproduce": "py scripts/build_guardrail_upgrade_autopilot_v1.py",
        "research_only": True,
    }
    BUILD_REPORT.parent.mkdir(parents=True, exist_ok=True)
    BUILD_REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.out_json} state={doc['autopilot_state']} queue={len(doc['execution_queue'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
