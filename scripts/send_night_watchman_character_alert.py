# @MKM12-METADATA
# Type: Engine
# Vector: {S:0.5, L:0.5, K:0.5, M:0.7}
# Purpose: Night Watchman character-map alert (dry-run or Slack webhook).
"""Send optional Slack alert summarizing pixel battalion public map + decision."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib import error, request

ROOT = Path(__file__).resolve().parents[1]
DOTENV = ROOT / ".env"
PUBLIC_MAP = ROOT / "docs" / "final" / "artifacts" / "pixel_battalion_character_map_public_latest.json"
ARTIFACT = ROOT / "docs" / "final" / "artifacts" / "night_watchman_character_alert_latest.json"


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
        if key in os.environ:
            continue
        os.environ[key] = value


def _webhook() -> str:
    # Dedicated Night Watchman URL first; then generic Slack; then PIN lookup
    # (same Incoming Webhook JSON body) so scheduled SOP can succeed when only
    # PIN_LOOKUP_ALERT_WEBHOOK_URL is configured in .env.
    return (
        os.getenv("NIGHT_WATCHMAN_WEBHOOK_URL", "").strip()
        or os.getenv("FACT_SAFE_SLACK_WEBHOOK_URL", "").strip()
        or os.getenv("SLACK_WEBHOOK_URL", "").strip()
        or os.getenv("PIN_LOOKUP_ALERT_WEBHOOK_URL", "").strip()
    )


def _post_slack(webhook: str, text: str) -> None:
    body = json.dumps({"text": text}).encode("utf-8")
    req = request.Request(
        webhook,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    try:
        with request.urlopen(req, timeout=30) as resp:
            if getattr(resp, "status", 200) >= 400:
                raise RuntimeError(f"webhook HTTP {getattr(resp, 'status', '?')}")
    except error.HTTPError as e:
        raise RuntimeError(f"webhook HTTP {e.code}: {e.reason}") from e


def main() -> None:
    _load_env_from_dotenv(DOTENV)
    p = argparse.ArgumentParser()
    p.add_argument("--decision", default="PASS")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    if not PUBLIC_MAP.exists():
        raise SystemExit(f"public map missing: {PUBLIC_MAP}")
    doc = json.loads(PUBLIC_MAP.read_text(encoding="utf-8"))
    n = len(doc.get("pilot_characters") or [])
    base = doc.get("public_base_url") or ""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    text = (
        f"*Night Watchman — Pixel Battalion*\n"
        f"- decision: `{args.decision}`\n"
        f"- characters: {n}\n"
        f"- public_base_url: {base}\n"
        f"- utc: {ts}"
    )
    record = {
        "schema": "night_watchman_character_alert_v1",
        "utc": ts,
        "decision": args.decision,
        "dry_run": bool(args.dry_run),
        "character_count": n,
        "public_base_url": base,
        "webhook_sent": False,
    }
    if args.dry_run:
        record["webhook_sent"] = False
        ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
        ARTIFACT.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(text)
        print(f"[dry-run] wrote {ARTIFACT}")
        return

    wh = _webhook()
    if not wh:
        raise SystemExit(
            "NIGHT_WATCHMAN_WEBHOOK_URL (or FACT_SAFE_SLACK_WEBHOOK_URL / SLACK_WEBHOOK_URL / PIN_LOOKUP_ALERT_WEBHOOK_URL) required for live alert"
        )
    _post_slack(wh, text)
    record["webhook_sent"] = True
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Sent Night Watchman alert ({n} chars), artifact {ARTIFACT}")


if __name__ == "__main__":
    main()
