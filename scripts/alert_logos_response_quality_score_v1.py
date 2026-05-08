#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import request

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCORE = ROOT / "docs" / "final" / "artifacts" / "logos_response_quality_score_v1_latest.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "logos_response_quality_score_alert_latest.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def post_webhook(url: str, payload: dict[str, Any]) -> tuple[bool, str]:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with request.urlopen(req, timeout=10) as resp:  # nosec - controlled webhook call
            return True, f"http_{resp.status}"
    except Exception as exc:  # pragma: no cover
        return False, f"error:{exc}"


def main() -> int:
    ap = argparse.ArgumentParser(description="Dispatch alert when logos quality score drops below threshold.")
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--overall-min", type=float, default=8.0)
    ap.add_argument("--webhook-url", default="")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    score_path = args.score_json if args.score_json.is_absolute() else ROOT / args.score_json
    if not score_path.is_file():
        raise SystemExit(f"Missing --score-json: {score_path}")
    score = load_json(score_path)
    scores = score.get("scores") if isinstance(score.get("scores"), dict) else {}
    overall = float(scores.get("overall") or 0.0)
    overall_100 = scores.get("overall_100")
    if overall_100 is None:
        overall_100 = round(overall * 10.0, 2)
    else:
        overall_100 = float(overall_100)
    grade = str(score.get("grade") or "UNKNOWN")
    alert_needed = overall < float(args.overall_min)

    webhook_url = (
        args.webhook_url.strip()
        or os.getenv("MKM_LOGOS_QUALITY_ALERT_WEBHOOK_URL", "").strip()
        or os.getenv("OPS_ALARM_WEBHOOK_URL", "").strip()
    )
    payload = {
        "schema": "logos_response_quality_alert_v1",
        "generated_at_utc": utc_now(),
        "overall": overall,
        "grade": grade,
        "overall_min": float(args.overall_min),
        "alert_needed": alert_needed,
        "score_json": str(score_path).replace("\\", "/"),
    }

    dispatched = False
    dispatch_result = "not_needed"
    if alert_needed:
        if not webhook_url:
            dispatch_result = "no_webhook_configured"
        elif args.dry_run:
            dispatch_result = "dry_run"
        else:
            dispatched, dispatch_result = post_webhook(webhook_url, payload)

    out = {
        "schema": "logos_response_quality_score_alert_result_v1",
        "generated_at_utc": utc_now(),
        "score_json": str(score_path).replace("\\", "/"),
        "alert_needed": alert_needed,
        "webhook_configured": bool(webhook_url),
        "webhook_dispatched": dispatched,
        "dispatch_result": dispatch_result,
        "overall": overall,
        "overall_100": overall_100,
        "grade": grade,
        "overall_min": float(args.overall_min),
    }
    out_path = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "alert_needed": alert_needed, "dispatch_result": dispatch_result}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
