#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IN = ROOT / "reports" / "mkm_compose_api_audit_summary_latest.json"
DEFAULT_OUT = ROOT / "reports" / "mkm_compose_api_audit_alert_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _f(v: Any, d: float = 0.0) -> float:
    return float(v) if isinstance(v, (int, float)) else d


def main() -> int:
    ap = argparse.ArgumentParser(description="Check compose API audit health against thresholds.")
    ap.add_argument("--input-json", type=Path, default=DEFAULT_IN)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--non-200-ratio-threshold", type=float, default=0.10)
    ap.add_argument("--min-total", type=int, default=20, help="Minimum sample size before hard alerting.")
    args = ap.parse_args()

    src = args.input_json if args.input_json.is_absolute() else ROOT / args.input_json
    doc = _read_json(src)
    ratios = doc.get("ratios") if isinstance(doc.get("ratios"), dict) else {}
    counts = doc.get("counts") if isinstance(doc.get("counts"), dict) else {}

    total = int(counts.get("total") or 0)
    non_200_ratio = _f(ratios.get("status_non_200_ratio"), 0.0)

    alerts: list[dict[str, Any]] = []
    status = "OK"
    if total >= args.min_total:
        if non_200_ratio > args.non_200_ratio_threshold:
            alerts.append(
                {
                    "type": "status_non_200_ratio_high",
                    "value": round(non_200_ratio, 6),
                    "threshold": round(args.non_200_ratio_threshold, 6),
                }
            )
        if alerts:
            status = "ALERT"
    else:
        status = "INSUFFICIENT_SAMPLE"

    out = {
        "schema": "mkm_compose_api_audit_alert_v1",
        "generated_at_utc": _now(),
        "status": status,
        "input_json": str(src.resolve()),
        "thresholds": {
            "non_200_ratio": args.non_200_ratio_threshold,
            "min_total": args.min_total,
        },
        "observed": {
            "total": total,
            "status_non_200_ratio": round(non_200_ratio, 6),
        },
        "alerts": alerts,
    }

    out_path = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "status": status, "out": str(out_path)}, ensure_ascii=False))
    return 0 if status != "ALERT" else 2


if __name__ == "__main__":
    raise SystemExit(main())
