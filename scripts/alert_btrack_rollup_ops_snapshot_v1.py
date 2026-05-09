from __future__ import annotations

import argparse
import json
import os
import urllib.request
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


def main() -> int:
    ap = argparse.ArgumentParser(description="Alert when B-track rollup ops snapshot is not healthy.")
    ap.add_argument("--snapshot-json", default="docs/final/artifacts/btrack_rollup_ops_snapshot_latest.json")
    ap.add_argument("--out", default="docs/final/artifacts/btrack_rollup_ops_alert_latest.json")
    ap.add_argument("--always-log", action="store_true")
    args = ap.parse_args()

    root = Path(__file__).resolve().parents[1]
    snapshot_path = (root / args.snapshot_json).resolve()
    out_path = (root / args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    snap = read_json(snapshot_path)
    if snap is None:
        payload = {
            "schema": "btrack_rollup_ops_alert_v1",
            "generated_at_utc": utc_now_iso(),
            "status": "snapshot_missing",
            "alert_sent": False,
            "snapshot_json": str(snapshot_path),
        }
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"WROTE: {out_path}")
        return 1

    summary = snap.get("summary") if isinstance(snap.get("summary"), dict) else {}
    ops_watch_ok = bool((summary or {}).get("ops_watch_ok"))
    payload: dict[str, Any] = {
        "schema": "btrack_rollup_ops_alert_v1",
        "generated_at_utc": utc_now_iso(),
        "status": "ok" if ops_watch_ok else "alert",
        "ops_watch_ok": ops_watch_ok,
        "all_artifacts_exist": bool((summary or {}).get("all_artifacts_exist")),
        "all_tasks_registered": bool((summary or {}).get("all_tasks_registered")),
        "default_task_ready": bool((summary or {}).get("default_task_ready")),
        "extended_task_ready": bool((summary or {}).get("extended_task_ready")),
        "snapshot_json": str(snapshot_path),
        "alert_sent": False,
    }

    webhook = os.getenv("OPS_ALARM_WEBHOOK_URL") or os.getenv("COMPRESSION_KPI_ALARM_WEBHOOK_URL")
    if not ops_watch_ok and webhook:
        body = json.dumps(
            {
                "event": "btrack_rollup_ops_snapshot",
                "kind": "warning",
                "message": "B-track rollup ops snapshot not healthy",
                "ops_watch_ok": False,
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
    elif not ops_watch_ok:
        payload["alert_skipped_reason"] = "webhook_not_configured"

    if args.always_log or (not ops_watch_ok):
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"WROTE: {out_path}")

    return 0 if ops_watch_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

