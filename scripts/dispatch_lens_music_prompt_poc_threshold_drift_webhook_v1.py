#!/usr/bin/env python3
"""Dispatch lens-music prompt PoC threshold drift state to optional webhook."""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, request

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_DRIFT = ART / "lens_music_prompt_poc_threshold_recommendation_drift_state_latest.json"
DEFAULT_OUT = ART / "lens_music_prompt_poc_threshold_recommendation_drift_webhook_dispatch_latest.json"


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
    ap.add_argument("--drift-json", type=Path, default=DEFAULT_DRIFT)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--webhook-env", type=str, default="LENS_MUSIC_PROMPT_POC_THRESHOLD_DRIFT_WEBHOOK_URL")
    ap.add_argument("--strict-mode-env", type=str, default="ENABLE_WEBHOOK_STRICT_MODE")
    ap.add_argument("--webhook-url", type=str, default="")
    args = ap.parse_args()

    drift = _read_json(args.drift_json)
    has_core = bool(drift and str(drift.get("schema", "")).strip())
    drift_state = str(drift.get("state") or "UNKNOWN").strip().upper()
    webhook = str(args.webhook_url or "").strip() or str(os.environ.get(args.webhook_env, "")).strip()
    strict_mode = str(os.environ.get(args.strict_mode_env, "")).strip().lower() in {"1", "true", "yes", "on"}
    should_dispatch = has_core and bool(webhook) and drift_state == "WATCH"

    payload = {
        "source": "lens_music_prompt_poc_threshold_drift_webhook_v1",
        "generated_at_utc": _iso_now(),
        "track": "B",
        "advisory_only": True,
        "drift": {
            "state": drift.get("state"),
            "reason": drift.get("reason"),
            "deltas": drift.get("deltas"),
            "checks": drift.get("checks"),
            "bounds": drift.get("bounds"),
        },
        "compliance_note": "Research lane advisory only. No automatic promotion/trading decision.",
        "evidence_ref": str(args.drift_json).replace("\\", "/"),
    }

    out: dict[str, Any] = {
        "schema": "lens_music_prompt_poc_threshold_recommendation_drift_webhook_dispatch_v1",
        "generated_at_utc": _iso_now(),
        "inputs": {
            "drift_json": str(args.drift_json).replace("\\", "/"),
            "webhook_env": args.webhook_env,
            "webhook_url_override": bool(str(args.webhook_url or "").strip()),
        },
        "decision": {
            "has_core_inputs": has_core,
            "drift_state": drift_state,
            "webhook_configured": bool(webhook),
            "webhook_policy_mode": "strict" if strict_mode else "best_effort",
            "dispatch_only_on_watch": True,
            "should_dispatch": should_dispatch,
        },
        "payload_preview": payload,
    }

    if should_dispatch:
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
        out["dispatch"] = {"status": "skipped", "reason": "missing_drift_input"}
    elif not webhook:
        out["dispatch"] = {"status": "skipped", "reason": "webhook_not_configured", "skip_classification": "config_missing_intent_unknown"}
    else:
        out["dispatch"] = {"status": "skipped", "reason": "drift_state_not_watch", "skip_classification": "policy_expected_not_watch"}

    if strict_mode and not webhook:
        out["dispatch"] = {"status": "failed", "reason": "webhook_required_but_missing", "policy_mode": "strict"}

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "dispatch_status": (out.get("dispatch") or {}).get("status"), "output_json": str(args.output_json)}))
    return 1 if strict_mode and not webhook else 0


if __name__ == "__main__":
    raise SystemExit(main())
