#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Engine
# Vector: {S:0.8, L:0.8, K:0.7, M:0.7}
# Balance: 89
# Purpose: Dispatch one-shot alert when completion_ready stays true for 24h.
# Keywords: completion, 24h, alert, webhook, dedupe
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib import error, request

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_utc(ts: str) -> datetime | None:
    try:
        return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    out: list[dict[str, Any]] = []
    for ln in path.read_text(encoding="utf-8-sig").splitlines():
        if not ln.strip():
            continue
        try:
            obj = json.loads(ln)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            out.append(obj)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--completion-gate-json", type=Path, default=ART / "genius_governance_completion_gate_latest.json")
    ap.add_argument("--health-history-jsonl", type=Path, default=ART / "genius_governance_scheduler_health_history_log.jsonl")
    ap.add_argument("--state-json", type=Path, default=ART / "genius_governance_completion_24h_alert_state_latest.json")
    ap.add_argument("--output-json", type=Path, default=ART / "genius_governance_completion_24h_alert_dispatch_latest.json")
    ap.add_argument("--required-hours", type=float, default=24.0)
    ap.add_argument("--webhook-env", type=str, default="OPS_ALARM_WEBHOOK_URL")
    args = ap.parse_args()

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=float(args.required_hours))
    completion = _read_json(args.completion_gate_json)
    completion_ready = bool(completion.get("completion_ready"))

    rows = _read_jsonl(args.health_history_jsonl)
    window = []
    for row in rows:
        dt = _parse_utc(str(row.get("ts_utc") or ""))
        if dt is None or dt < cutoff:
            continue
        window.append((dt, str(row.get("health_status") or "UNKNOWN").upper()))
    window.sort(key=lambda x: x[0])
    covered_hours = 0.0
    if window:
        covered_hours = (window[-1][0] - window[0][0]).total_seconds() / 3600.0
    all_pass = bool(window) and all(s == "PASS" for _, s in window)
    stable_24h = completion_ready and all_pass and covered_hours >= float(args.required_hours) * 0.95

    state = _read_json(args.state_json)
    already_sent = bool(state.get("alert_sent_for_stable_24h"))
    should_dispatch = stable_24h and not already_sent
    webhook = str(os.environ.get(args.webhook_env, "")).strip()

    out: dict[str, Any] = {
        "schema": "genius_governance_completion_24h_alert_dispatch_v1",
        "generated_at_utc": _iso_now(),
        "inputs": {
            "completion_gate_json": str(args.completion_gate_json).replace("\\", "/"),
            "health_history_jsonl": str(args.health_history_jsonl).replace("\\", "/"),
            "required_hours": float(args.required_hours),
            "webhook_env": args.webhook_env,
        },
        "current": {
            "completion_ready": completion_ready,
            "window_rows": len(window),
            "window_covered_hours": round(covered_hours, 3),
            "all_pass_in_window": all_pass,
            "stable_24h": stable_24h,
        },
        "decision": {
            "already_sent": already_sent,
            "should_dispatch": should_dispatch,
            "webhook_configured": bool(webhook),
        },
    }

    if should_dispatch and webhook:
        payload = {
            "source": "genius_governance_completion_gate_v1",
            "severity": "INFO",
            "status": "COMPLETION_READY_24H",
            "completion_ready": True,
            "window_covered_hours": round(covered_hours, 3),
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
            state = {
                "schema": "genius_governance_completion_24h_alert_state_v1",
                "updated_at_utc": _iso_now(),
                "alert_sent_for_stable_24h": True,
            }
        except (error.URLError, TimeoutError) as exc:
            out["dispatch"] = {"status": "failed", "error": str(exc)}
    elif should_dispatch and not webhook:
        out["dispatch"] = {"status": "skipped", "reason": "webhook_not_configured"}
    else:
        out["dispatch"] = {"status": "skipped", "reason": "not_stable_24h_or_already_sent"}
        if not stable_24h:
            state = {
                "schema": "genius_governance_completion_24h_alert_state_v1",
                "updated_at_utc": _iso_now(),
                "alert_sent_for_stable_24h": False,
            }

    args.state_json.parent.mkdir(parents=True, exist_ok=True)
    args.state_json.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output_json": str(args.output_json).replace("\\", "/"), "dispatch_status": out["dispatch"]["status"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
