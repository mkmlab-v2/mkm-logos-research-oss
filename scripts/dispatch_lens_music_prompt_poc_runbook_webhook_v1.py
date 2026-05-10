#!/usr/bin/env python3
"""Dispatch lens music prompt PoC runbook to optional webhook (M29)."""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, request

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUNBOOK = ROOT / "docs" / "final" / "artifacts" / "lens_music_prompt_poc_runbook_latest.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "lens_music_prompt_poc_runbook_webhook_dispatch_latest.json"
DEFAULT_HISTORY_LOG = ROOT / "reports" / "lens_music_prompt_poc_runbook_webhook_history.jsonl"


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


def _append_history_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--runbook-json", type=Path, default=DEFAULT_RUNBOOK)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--webhook-env", type=str, default="LENS_MUSIC_PROMPT_POC_RUNBOOK_WEBHOOK_URL")
    ap.add_argument("--require-watch", action="store_true", help="Dispatch only when runbook state is WATCH.")
    ap.add_argument(
        "--require-high-priority",
        action="store_true",
        help="Dispatch only when at least one recommendation has priority=high.",
    )
    ap.add_argument("--history-jsonl", type=Path, default=DEFAULT_HISTORY_LOG)
    ap.add_argument("--no-append-history", action="store_true", help="Do not append to history JSONL.")
    args = ap.parse_args()

    runbook = _read_json(args.runbook_json)
    has_core = bool(runbook and str(runbook.get("schema", "")).strip())
    webhook = str(os.environ.get(args.webhook_env, "")).strip()
    state = str(runbook.get("state") or "UNKNOWN")
    recs = list(runbook.get("recommendations") or [])
    has_high = any(str(r.get("priority") or "").strip().lower() == "high" for r in recs if isinstance(r, dict))
    top = recs[0] if recs else {}

    watch_ok = (not args.require_watch) or state == "WATCH"
    high_ok = (not args.require_high_priority) or has_high
    should_dispatch = has_core and bool(webhook) and watch_ok and high_ok

    payload = {
        "source": "lens_music_prompt_poc_runbook_webhook_v1",
        "generated_at_utc": _iso_now(),
        "track": "B",
        "advisory_only": True,
        "runbook": {
            "schema": runbook.get("schema"),
            "state": state,
            "recommendation_count": len(recs),
            "top_recommendation_cause": top.get("cause"),
            "top_recommendation_priority": top.get("priority"),
        },
        "compliance_note": "Research lane advisory only. No automatic promotion/trading decision.",
        "evidence_ref": str(args.runbook_json).replace("\\", "/"),
    }

    out: dict[str, Any] = {
        "schema": "lens_music_prompt_poc_runbook_webhook_dispatch_v1",
        "generated_at_utc": _iso_now(),
        "inputs": {
            "runbook_json": str(args.runbook_json).replace("\\", "/"),
            "webhook_env": args.webhook_env,
            "require_watch": bool(args.require_watch),
            "require_high_priority": bool(args.require_high_priority),
        },
        "decision": {
            "has_core_inputs": has_core,
            "webhook_configured": bool(webhook),
            "watch_gate_passed": watch_ok,
            "high_priority_gate_passed": high_ok,
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
        out["dispatch"] = {"status": "skipped", "reason": "missing_runbook_input"}
    elif not webhook:
        out["dispatch"] = {"status": "skipped", "reason": "webhook_not_configured"}
    elif not watch_ok:
        out["dispatch"] = {"status": "skipped", "reason": "watch_gate_not_met"}
    else:
        out["dispatch"] = {"status": "skipped", "reason": "high_priority_gate_not_met"}

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if not args.no_append_history:
        dblock = out.get("dispatch") or {}
        hist_row: dict[str, Any] = {
            "schema": "lens_music_prompt_poc_runbook_webhook_history_row_v1",
            "ts_utc": str(out.get("generated_at_utc") or _iso_now()),
            "dispatch_status": dblock.get("status"),
            "runbook_state": state,
            "require_watch": bool(args.require_watch),
            "require_high_priority": bool(args.require_high_priority),
        }
        st = str(dblock.get("status") or "")
        if st == "skipped":
            hist_row["skip_reason"] = dblock.get("reason")
        elif st == "failed":
            hist_row["error"] = dblock.get("error")
        elif st == "sent":
            hist_row["http_status"] = dblock.get("http_status")
        _append_history_jsonl(args.history_jsonl, hist_row)

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
