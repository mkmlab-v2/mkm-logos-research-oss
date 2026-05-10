#!/usr/bin/env python3
"""Dispatch lens music prompt brake trend status to optional webhook (M25)."""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, request

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TREND = ROOT / "docs" / "final" / "artifacts" / "lens_music_prompt_brake_trend_latest.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "lens_music_prompt_brake_trend_webhook_dispatch_latest.json"


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


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--trend-json", type=Path, default=DEFAULT_TREND)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--webhook-env", type=str, default="LENS_MUSIC_PROMPT_BRAKE_WEBHOOK_URL")
    args = ap.parse_args()

    trend = _read_json(args.trend_json)
    has_core = bool(trend and str(trend.get("schema", "")).strip())
    webhook = str(os.environ.get(args.webhook_env, "")).strip()
    top = list(trend.get("top_triggers") or [])
    top_first = top[0] if top else {}

    payload = {
        "source": "lens_music_prompt_brake_trend_webhook_v1",
        "generated_at_utc": _iso_now(),
        "track": "B",
        "advisory_only": True,
        "trend": {
            "schema": trend.get("schema"),
            "state": trend.get("state"),
            "rows_scanned": trend.get("rows_scanned"),
            "auto_brake_active_rate": trend.get("auto_brake_active_rate"),
            "top_trigger": top_first.get("trigger"),
            "top_trigger_count": top_first.get("count"),
        },
        "compliance_note": "Research lane advisory only. No automatic promotion/trading decision.",
        "evidence_ref": str(args.trend_json).replace("\\", "/"),
    }

    out: dict[str, Any] = {
        "schema": "lens_music_prompt_brake_trend_webhook_dispatch_v1",
        "generated_at_utc": _iso_now(),
        "inputs": {
            "trend_json": str(args.trend_json).replace("\\", "/"),
            "webhook_env": args.webhook_env,
        },
        "decision": {
            "has_core_inputs": has_core,
            "webhook_configured": bool(webhook),
            "should_dispatch": has_core and bool(webhook),
        },
        "payload_preview": payload,
    }

    if has_core and webhook:
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
    elif not has_core:
        out["dispatch"] = {"status": "skipped", "reason": "missing_trend_input"}
    else:
        out["dispatch"] = {"status": "skipped", "reason": "webhook_not_configured"}

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "dispatch_status": (out.get("dispatch") or {}).get("status"),
                "output_json": str(args.output_json).replace("\\", "/"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
