#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "docs" / "final" / "artifacts"
READINESS_DEFAULT = ART / "pointerguard_ops_readiness_latest.json"
ALERT_DEFAULT = ART / "pointerguard_ops_alert_delivery_latest.json"
OUT_DEFAULT = ART / "pointerguard_ops_status_dashboard_latest.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--readiness-json", type=Path, default=READINESS_DEFAULT)
    ap.add_argument("--alert-json", type=Path, default=ALERT_DEFAULT)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    readiness_path = args.readiness_json if args.readiness_json.is_absolute() else ROOT / args.readiness_json
    alert_path = args.alert_json if args.alert_json.is_absolute() else ROOT / args.alert_json
    out_path = args.out if args.out.is_absolute() else ROOT / args.out

    readiness = _read_json(readiness_path) if readiness_path.exists() else {}
    alert = _read_json(alert_path) if alert_path.exists() else {}
    checks = readiness.get("checks", [])
    failed = [c for c in checks if isinstance(c, dict) and not bool(c.get("ok", False))]

    out_doc = {
        "schema": "pointerguard_ops_status_dashboard_v1",
        "generated_at_utc": _now_utc(),
        "summary": {
            "readiness_all_ok": bool(readiness.get("all_ok", False)),
            "failed_check_count": len(failed),
            "latest_alert_should_send": bool(alert.get("alert", {}).get("should_send", False)),
            "latest_alert_severity": str(alert.get("alert", {}).get("severity", "INFO")),
            "latest_alert_status": str(alert.get("delivery", {}).get("status", "unknown")),
        },
        "failed_checks_preview": failed[:5],
        "sources": {
            "readiness_json": str(readiness_path),
            "alert_json": str(alert_path),
        },
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "readiness_all_ok": out_doc["summary"]["readiness_all_ok"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
