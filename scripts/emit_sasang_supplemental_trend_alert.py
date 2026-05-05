#!/usr/bin/env python3
"""Emit non-gating operator alert artifact from Sasang supplemental trend."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_TREND = ART / "sasang_supplemental_insight_trend_latest.json"
DEFAULT_OUT = ART / "sasang_supplemental_trend_alert_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--trend", type=Path, default=DEFAULT_TREND)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    trend_doc = _read(args.trend)
    if not isinstance(trend_doc, dict):
        print(f"ERROR: missing trend artifact: {args.trend}")
        return 2

    trend_alert = bool(trend_doc.get("alert", False))
    trend_status = str(trend_doc.get("trend_status") or "MISSING")
    delta = float(trend_doc.get("delta") or 0.0)

    notify_operator = trend_alert
    severity = "warn" if trend_alert else "info"
    payload = {
        "schema": "sasang_supplemental_trend_alert_v1",
        "generated_at_utc": _now(),
        "non_gating_policy": True,
        "trend_artifact": str(args.trend.resolve()),
        "trend_status": trend_status,
        "delta": round(delta, 6),
        "notify_operator": notify_operator,
        "severity": severity,
        "message": (
            f"Sasang supplemental trend alert: status={trend_status}, delta={delta:.6f}"
            if notify_operator
            else f"Sasang supplemental trend stable: status={trend_status}, delta={delta:.6f}"
        ),
        "impact_on_go_no_go": "none_non_gating",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    print(f"notify_operator={notify_operator}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
