# @MKM12-METADATA
# Type: Engine
# Vector: {S:0.9, L:0.7, K:0.5, M:0.6}
# Balance: 89
# Purpose: Send Fact-Safe broadcast summary to Slack webhook.
# Keywords: slack, webhook, broadcast, fact-safe
"""Send fact-safe broadcast summary to Slack webhook."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from urllib import error, request

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BROADCAST_JSON = (
    ROOT / "projects" / "bitcoin-trading" / "memory" / "v2" / "briefs" / "fact_safe_multilens_broadcast_latest.json"
)


def _safe_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
        return doc if isinstance(doc, dict) else {}
    except Exception:
        return {}


def build_slack_text(payload: dict) -> str:
    return "\n".join(
        [
            ":shield: *Fact-Safe Monthly Broadcast*",
            f"- generated_at_utc: {payload.get('ts_utc')}",
            f"- reliability_badge: {payload.get('reliability_badge')}",
            f"- high_reliability_decision: {payload.get('high_reliability_decision')}",
            f"- gate_reason: {payload.get('gate_reason')}",
            f"- net: {payload.get('net')}",
            f"- history_samples: {payload.get('history_samples')}",
            f"- history_net_delta: {payload.get('history_net_delta')}",
            (
                f"- overlap_drift_alert: {payload.get('overlap_drift_alert')} "
                f"(threshold={payload.get('overlap_drift_alert_threshold')})"
            ),
        ]
    )


def post_to_slack(webhook_url: str, text: str) -> None:
    data = json.dumps({"text": text}).encode("utf-8")
    req = request.Request(
        webhook_url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8", errors="ignore").strip()
            if resp.status >= 300:
                raise RuntimeError(f"Slack webhook failed: HTTP {resp.status}, body={body}")
    except error.URLError as exc:
        raise RuntimeError(f"Slack webhook request failed: {exc}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description="Send Fact-Safe broadcast to Slack")
    parser.add_argument("--input", default=str(DEFAULT_BROADCAST_JSON))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--webhook-url",
        default=(
            os.getenv("FACT_SAFE_SLACK_WEBHOOK_URL", "").strip()
            or os.getenv("SLACK_WEBHOOK_URL", "").strip()
        ),
    )
    args = parser.parse_args()

    payload = _safe_json(Path(args.input))
    if not payload:
        print(f"WARNING: broadcast payload missing or invalid: {args.input}")
        return 0

    text = build_slack_text(payload)
    print(text)
    if args.dry_run:
        print("DRY RUN: Slack message not sent.")
        return 0
    if not args.webhook_url:
        print("WARNING: FACT_SAFE_SLACK_WEBHOOK_URL/SLACK_WEBHOOK_URL not set; Slack send skipped.")
        return 0

    post_to_slack(args.webhook_url, text)
    print("Slack message sent successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
