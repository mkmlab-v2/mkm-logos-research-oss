#!/usr/bin/env python3
"""Dual-probe drift webhook stub — dry-run payload; optional live POST [HYPO]."""

from __future__ import annotations

import argparse
import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ALERT = ROOT / "reports/sasang_4agent_dual_probe_weekly_drift_alert_v1_latest.json"
OUT = ROOT / "reports/sasang_4agent_dual_probe_drift_webhook_stub_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _webhook_url(explicit: str | None) -> str:
    if explicit:
        return explicit.strip()
    return (
        (os.getenv("SASANG_DUAL_PROBE_DRIFT_WEBHOOK_URL") or "").strip()
        or (os.getenv("OPS_ALARM_WEBHOOK_URL") or "").strip()
    )


def build(*, live: bool = False, webhook_override: str | None = None) -> dict[str, Any]:
    alert = _load(ALERT)
    url = _webhook_url(webhook_override)
    payload = {
        "schema": "sasang_dual_probe_drift_webhook_payload_v1",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "send_gate": "HOLD",
        "alert_level": alert.get("alert_level"),
        "drift_status": alert.get("drift_status"),
        "message": alert.get("message"),
        "max_abs_mdd_drift": alert.get("max_abs_mdd_drift"),
    }
    post_ok = None
    post_status = "skipped_no_url"
    if live and url:
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                post_ok = 200 <= resp.status < 300
                post_status = f"http_{resp.status}"
        except Exception as exc:
            post_ok = False
            post_status = f"error:{type(exc).__name__}"

    stub_ok = alert.get("schema") == "sasang_4agent_dual_probe_weekly_drift_alert_v1" and alert.get("alert_ok") is True
    return {
        "schema": "sasang_4agent_dual_probe_drift_webhook_stub_v1",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "stub_ok": stub_ok,
        "live_post_requested": live,
        "webhook_configured": bool(url),
        "webhook_post_ok": post_ok,
        "webhook_post_status": post_status,
        "payload": payload,
        "alert_ref": str(ALERT).replace("\\", "/"),
        "reproduce": "py scripts/build_sasang_4agent_dual_probe_drift_webhook_stub_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--live", action="store_true", help="POST when webhook URL is configured")
    ap.add_argument("--webhook-url", default=None)
    args = ap.parse_args()
    doc = build(live=args.live, webhook_override=args.webhook_url)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["stub_ok"], "webhook_post_status": doc["webhook_post_status"]}))
    return 0 if doc["stub_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
