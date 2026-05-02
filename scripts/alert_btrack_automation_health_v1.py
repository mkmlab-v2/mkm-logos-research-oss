from __future__ import annotations

import argparse
import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def main() -> int:
    parser = argparse.ArgumentParser(description="Alert when B-track automation health is not ready.")
    parser.add_argument(
        "--snapshot-json",
        default="docs/final/artifacts/btrack_automation_health_snapshot_latest.json",
    )
    parser.add_argument(
        "--out",
        default="docs/final/artifacts/btrack_automation_health_alert_latest.json",
    )
    parser.add_argument(
        "--always-log",
        action="store_true",
        help="Write output artifact even when healthy",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    snapshot_path = (root / args.snapshot_json).resolve()
    out_path = (root / args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if not snapshot_path.exists():
        payload = {
            "schema": "btrack_automation_health_alert_v1",
            "generated_at_utc": utc_now_iso(),
            "status": "snapshot_missing",
            "alert_sent": False,
            "snapshot_json": str(snapshot_path),
        }
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"WROTE: {out_path}")
        return 1

    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    summary = snapshot.get("summary") or {}
    ops_ready = bool(summary.get("ops_ready"))

    payload = {
        "schema": "btrack_automation_health_alert_v1",
        "generated_at_utc": utc_now_iso(),
        "status": "ok" if ops_ready else "alert",
        "ops_ready": ops_ready,
        "all_tasks_ok": bool(summary.get("all_tasks_ok")),
        "all_artifacts_ok": bool(summary.get("all_artifacts_ok")),
        "snapshot_json": str(snapshot_path),
        "alert_sent": False,
    }

    webhook = os.getenv("OPS_ALARM_WEBHOOK_URL") or os.getenv("COMPRESSION_KPI_ALARM_WEBHOOK_URL")
    if not ops_ready and webhook:
        body = json.dumps(
            {
                "event": "btrack_automation_health",
                "kind": "warning",
                "message": "B-track automation health is not ready",
                "ops_ready": False,
                "snapshot_path": str(snapshot_path),
                "ts_utc": payload["generated_at_utc"],
            }
        ).encode("utf-8")
        req = urllib.request.Request(webhook, data=body, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:  # nosec B310
                payload["alert_http_status"] = getattr(resp, "status", None)
                payload["alert_sent"] = True
        except Exception as exc:  # pragma: no cover
            payload["alert_error"] = str(exc)
    elif not ops_ready:
        payload["alert_skipped_reason"] = "webhook_not_configured"

    if args.always_log or (not ops_ready):
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"WROTE: {out_path}")

    return 0 if ops_ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
