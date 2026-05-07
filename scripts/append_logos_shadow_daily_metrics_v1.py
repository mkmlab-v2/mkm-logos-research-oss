#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
REPORTS = ROOT / "reports"

DEFAULT_SUITE = ART / "logos_semantic_query_smoke_suite_latest.json"
DEFAULT_DRIFT = ART / "logos_semantic_drift_monitor_latest.json"
DEFAULT_PROMOTION = ART / "logos_shadow_promotion_status_latest.json"
DEFAULT_LOG = REPORTS / "logos_shadow_daily_metrics_log_v1.jsonl"
DEFAULT_LATEST = ART / "logos_shadow_daily_metrics_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _f(v: Any) -> float | None:
    return float(v) if isinstance(v, (int, float)) else None


def main() -> int:
    ap = argparse.ArgumentParser(description="Append daily Logos shadow quality metrics log.")
    ap.add_argument("--suite-json", type=Path, default=DEFAULT_SUITE)
    ap.add_argument("--drift-json", type=Path, default=DEFAULT_DRIFT)
    ap.add_argument("--promotion-json", type=Path, default=DEFAULT_PROMOTION)
    ap.add_argument("--output-log-jsonl", type=Path, default=DEFAULT_LOG)
    ap.add_argument("--output-latest-json", type=Path, default=DEFAULT_LATEST)
    args = ap.parse_args()

    suite_path = args.suite_json if args.suite_json.is_absolute() else ROOT / args.suite_json
    drift_path = args.drift_json if args.drift_json.is_absolute() else ROOT / args.drift_json
    promotion_path = args.promotion_json if args.promotion_json.is_absolute() else ROOT / args.promotion_json
    log_path = args.output_log_jsonl if args.output_log_jsonl.is_absolute() else ROOT / args.output_log_jsonl
    latest_path = args.output_latest_json if args.output_latest_json.is_absolute() else ROOT / args.output_latest_json

    for p in (suite_path, drift_path, promotion_path):
        if not p.is_file():
            raise SystemExit(f"Missing required json: {p}")

    suite = _read_json(suite_path)
    drift = _read_json(drift_path)
    promotion = _read_json(promotion_path)
    summary = suite.get("summary") if isinstance(suite.get("summary"), dict) else {}

    row = {
        "schema": "logos_shadow_daily_metrics_v1",
        "generated_at_utc": _now(),
        "shadow_grade": ((promotion.get("promotion") or {}).get("to")),
        "promotion_approved": ((promotion.get("promotion") or {}).get("approved")),
        "mean_top1_cosine": _f(summary.get("mean_top1_cosine")),
        "queries_ok": int(summary.get("queries_ok") or 0),
        "queries_error": int(summary.get("queries_error") or 0),
        "low_confidence": ((drift.get("guard") or {}).get("low_confidence") is True),
        "drift_decision": (drift.get("guard") or {}).get("decision"),
    }

    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")

    latest_path.parent.mkdir(parents=True, exist_ok=True)
    latest_path.write_text(json.dumps(row, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "log": str(log_path), "latest": str(latest_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

