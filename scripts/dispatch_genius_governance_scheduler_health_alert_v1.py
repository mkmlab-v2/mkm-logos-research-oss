#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Engine
# Vector: {S:0.8, L:0.7, K:0.8, M:0.5}
# Balance: 87
# Purpose: Dispatch scheduler health HOLD alert once per state transition.
# Keywords: webhook, alert, scheduler health, dedupe
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, request

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_HEALTH = ART / "genius_governance_scheduler_health_check_latest.json"
DEFAULT_HISTORY = ART / "genius_governance_scheduler_health_history_log.jsonl"
DEFAULT_OUT = ART / "genius_governance_scheduler_health_alert_dispatch_latest.json"
DEFAULT_MODE = ART / "genius_governance_scheduler_mode_signal_latest.json"
DEFAULT_KPI = ART / "genius_governance_scheduler_kpi_latest.json"
DEFAULT_COMPLETION = ART / "genius_governance_completion_gate_latest.json"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _tail_statuses(path: Path, n: int = 2) -> list[str]:
    if not path.is_file():
        return []
    lines = [ln for ln in path.read_text(encoding="utf-8-sig").splitlines() if ln.strip()]
    out: list[str] = []
    for ln in lines[-n:]:
        try:
            obj = json.loads(ln)
        except json.JSONDecodeError:
            continue
        out.append(str(obj.get("health_status") or "UNKNOWN").upper())
    return out


def _tail_hold_streak(path: Path, n: int = 20) -> int:
    statuses = _tail_statuses(path, n=n)
    streak = 0
    for s in reversed(statuses):
        if s == "HOLD":
            streak += 1
        else:
            break
    return streak


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--health-json", type=Path, default=DEFAULT_HEALTH)
    ap.add_argument("--history-jsonl", type=Path, default=DEFAULT_HISTORY)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--webhook-env", type=str, default="OPS_ALARM_WEBHOOK_URL")
    ap.add_argument("--min-hold-streak-to-dispatch", type=int, default=1)
    ap.add_argument("--mode-json", type=Path, default=DEFAULT_MODE)
    ap.add_argument("--kpi-json", type=Path, default=DEFAULT_KPI)
    ap.add_argument("--completion-json", type=Path, default=DEFAULT_COMPLETION)
    args = ap.parse_args()

    health = _read_json(args.health_json)
    mode_doc = _read_json(args.mode_json)
    kpi_doc = _read_json(args.kpi_json)
    completion_doc = _read_json(args.completion_json)
    current_status = str(health.get("status") or "UNKNOWN").upper()
    statuses = _tail_statuses(args.history_jsonl, n=2)
    prev_status = statuses[-2] if len(statuses) >= 2 else None
    hold_streak = _tail_hold_streak(args.history_jsonl, n=max(20, int(args.min_hold_streak_to_dispatch) + 5))
    should_dispatch = (
        current_status == "HOLD"
        and prev_status != "HOLD"
        and hold_streak >= int(args.min_hold_streak_to_dispatch)
    )
    webhook = str(os.environ.get(args.webhook_env, "")).strip()

    out: dict[str, Any] = {
        "schema": "genius_governance_scheduler_health_alert_dispatch_v1",
        "generated_at_utc": _iso_now(),
        "inputs": {
            "health_json": str(args.health_json).replace("\\", "/"),
            "history_jsonl": str(args.history_jsonl).replace("\\", "/"),
            "webhook_env": args.webhook_env,
            "mode_json": str(args.mode_json).replace("\\", "/"),
            "kpi_json": str(args.kpi_json).replace("\\", "/"),
            "completion_json": str(args.completion_json).replace("\\", "/"),
        },
        "decision": {
            "current_status": current_status,
            "previous_status": prev_status,
            "hold_streak": hold_streak,
            "min_hold_streak_to_dispatch": int(args.min_hold_streak_to_dispatch),
            "should_dispatch": should_dispatch,
            "webhook_configured": bool(webhook),
        },
    }
    if should_dispatch and webhook:
        payload = {
            "source": "genius_governance_scheduler_health_check_v1",
            "severity": "CRITICAL",
            "status": current_status,
            "summary": health.get("summary"),
            "mode_signal": ((mode_doc.get("mode_signal") or {}).get("mode")),
            "kpi_24h": ((kpi_doc.get("kpi") or {}).get("last_24h")),
            "completion_ready": bool(completion_doc.get("completion_ready")),
            "generated_at_utc": _iso_now(),
        }
        req = request.Request(
            webhook,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=10) as resp:
                code = int(resp.getcode())
            out["dispatch"] = {"status": "sent", "http_status": code}
        except (error.URLError, TimeoutError) as exc:
            out["dispatch"] = {"status": "failed", "error": str(exc)}
    elif should_dispatch and not webhook:
        out["dispatch"] = {"status": "skipped", "reason": "webhook_not_configured"}
    else:
        out["dispatch"] = {"status": "skipped", "reason": "no_new_hold_transition"}

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output_json": str(args.output_json).replace("\\", "/"), "dispatch_status": out["dispatch"]["status"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
