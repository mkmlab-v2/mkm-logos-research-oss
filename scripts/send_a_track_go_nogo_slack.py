#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Send weekly A-Track Go/No-Go status to Slack webhook.

Inputs:
- docs/final/artifacts/a_track_go_nogo_status_latest.json (default)

Env:
- A_TRACK_SLACK_WEBHOOK_URL (preferred)
- FACT_SAFE_SLACK_WEBHOOK_URL / SLACK_WEBHOOK_URL fallback
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
from urllib import error, request


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATUS_JSON = ROOT / "docs" / "final" / "artifacts" / "a_track_go_nogo_status_latest.json"
DOTENV_PATH = ROOT / ".env"
DEFAULT_LOG_JSONL = ROOT / "docs" / "final" / "artifacts" / "a_track_go_nogo_slack_delivery_log.jsonl"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_env_from_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if " #" in value:
            value = value.split(" #", 1)[0].strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        if not key:
            continue
        # Do not override already-set env.
        if key in os.environ:
            continue
        os.environ[key] = value


def _webhook_url() -> str:
    return (
        os.getenv("A_TRACK_SLACK_WEBHOOK_URL", "").strip()
        or os.getenv("FACT_SAFE_SLACK_WEBHOOK_URL", "").strip()
        or os.getenv("SLACK_WEBHOOK_URL", "").strip()
    )


def _safe_read_json(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
        return doc if isinstance(doc, dict) else {}
    except Exception:
        return {}


def _mask_webhook(url: str) -> str:
    if not url:
        return ""
    if len(url) <= 12:
        return "***"
    return url[:6] + "***" + url[-6:]


def _fmt_failed_reasons(reasons: Any) -> str:
    if not isinstance(reasons, list) or not reasons:
        return "none"
    # Keep plain ascii bullets for readability.
    return "\n".join([f"- {str(r)}" for r in reasons[:30]])


def build_slack_payload(status: Dict[str, Any]) -> Dict[str, Any]:
    result = status.get("result") or {}
    snapshot = status.get("snapshot") or {}

    overall = str(result.get("overall_go_no_go") or "UNKNOWN").upper()
    stage = str(result.get("recommended_stage") or "UNKNOWN")
    failed_reasons = result.get("failed_reasons") or []

    high_rel_decision = str(snapshot.get("high_reliability_decision") or "unknown").upper()
    price_locked = bool(snapshot.get("price_output_locked"))
    chronos_dir = snapshot.get("chronos_holdout_direction_match_rate")

    # Color is handled by legacy attachments (safe for incoming webhooks).
    if overall == "GO":
        color = "#36a64f"  # green
    elif overall == "HOLD":
        color = "#ffae42"  # orange
    else:
        color = "#d00000"  # red (NO_GO / unknown / malformed)

    title = f"A-Track Status: {overall} | {stage}"
    failed_text = _fmt_failed_reasons(failed_reasons)

    lines: List[str] = [
        title,
        f"- high_reliability_decision: {high_rel_decision}",
        f"- price_output_locked: {price_locked}",
        f"- chronos_holdout_direction_match_rate: {chronos_dir}",
        f"- failed_reasons:\n{failed_text}",
    ]
    ts = status.get("meta", {}).get("generated_at_utc") or _utc_now_iso()

    payload: Dict[str, Any] = {
        "text": title,
        "attachments": [
            {
                "color": color,
                "fields": [
                    {"title": "overall_go_no_go", "value": overall, "short": True},
                    {"title": "recommended_stage", "value": stage, "short": True},
                    {"title": "generated_at_utc", "value": str(ts), "short": False},
                ],
                "mrkdwn_in": ["fields"],
            }
        ],
    }
    # Also include full text in a single block for clarity.
    payload["text"] = "\n".join(lines)  # plain text; no markdown dependency
    return payload


def post_to_slack(webhook: str, payload: Dict[str, Any], timeout_s: int = 15) -> None:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = request.Request(
        webhook,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with request.urlopen(req, timeout=timeout_s) as resp:
            # Incoming-webhook usually returns 200 with empty body.
            _ = resp.read()
    except error.URLError as exc:
        raise RuntimeError(f"Slack webhook request failed: {exc}") from exc


def append_delivery_log(path: Path, row: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Send A-Track Go/No-Go to Slack.")
    parser.add_argument("--input", default=str(DEFAULT_STATUS_JSON), help="Status JSON path")
    parser.add_argument("--dry-run", action="store_true", help="Do not send webhook")
    parser.add_argument("--log-out", default=str(DEFAULT_LOG_JSONL), help="Append delivery log JSONL")
    parser.add_argument("--timeout-s", type=int, default=15)
    args = parser.parse_args()

    _load_env_from_dotenv(DOTENV_PATH)

    status_path = Path(args.input).resolve()
    status = _safe_read_json(status_path)
    if not status:
        # Fail-safe: missing status file => still send an informative NO_GO message.
        status = {"meta": {"generated_at_utc": _utc_now_iso()}, "result": {"overall_go_no_go": "NO_GO"}}

    payload = build_slack_payload(status)

    webhook = _webhook_url()
    wh_mask = _mask_webhook(webhook)
    dry = bool(args.dry_run)

    record = {
        "schema": "a_track_go_nogo_slack_delivery_v1",
        "utc": _utc_now_iso(),
        "input_status_path": str(status_path),
        "webhook_url_masked": wh_mask,
        "dry_run": dry,
        "webhook_sent": False,
        "payload_summary": {
            "overall_go_no_go": (status.get("result") or {}).get("overall_go_no_go"),
            "recommended_stage": (status.get("result") or {}).get("recommended_stage"),
        },
    }

    if dry:
        append_delivery_log(Path(args.log_out).resolve(), record)
        print("dry-run: not sending Slack webhook")
        return 0

    if not webhook:
        # No webhook configured: treat as local failure but keep log.
        record["error"] = "missing_webhook_url"
        append_delivery_log(Path(args.log_out).resolve(), record)
        raise SystemExit("Slack webhook URL not set (A_TRACK_SLACK_WEBHOOK_URL / FACT_SAFE_SLACK_WEBHOOK_URL / SLACK_WEBHOOK_URL)")

    post_to_slack(webhook, payload, timeout_s=int(args.timeout_s))
    record["webhook_sent"] = True
    append_delivery_log(Path(args.log_out).resolve(), record)
    print("sent Slack webhook")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

