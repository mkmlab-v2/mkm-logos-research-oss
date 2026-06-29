#!/usr/bin/env python3
"""POST Saving the News public-event stub to local public_event_gateway (research_only)."""
from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
STUB = ROOT / "docs/final/artifacts/saving_the_news_public_event_ingest_stub_v1.json"
DEFAULT_CHARACTER = "dog_sentinel"


def prepare_payload(
    base: dict[str, Any],
    *,
    event_id_suffix: str = "",
    active_character_id: str = DEFAULT_CHARACTER,
) -> dict[str, Any]:
    out = deepcopy(base)
    if event_id_suffix:
        eid = str(out.get("event_id", "event"))
        out["event_id"] = f"{eid}-{event_id_suffix}"
    out["active_character_id"] = active_character_id
    if not out.get("timestamp"):
        out["timestamp"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if not out.get("schema_version"):
        out["schema_version"] = "public-event.v1"
    return out


def _post_json(url: str, payload: dict[str, Any], token: str | None) -> dict[str, Any]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("X-Public-Event-Token", token)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--api-base", default="http://127.0.0.1:8788")
    ap.add_argument("--stub-json", type=Path, default=STUB)
    ap.add_argument("--event-id-suffix", default="local")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not args.stub_json.is_file():
        print(f"Missing stub: {args.stub_json}")
        return 2

    base = json.loads(args.stub_json.read_text(encoding="utf-8"))
    payload = prepare_payload(base, event_id_suffix=args.event_id_suffix)
    if args.dry_run:
        print(json.dumps({"ok": True, "dry_run": True, "payload": payload}, ensure_ascii=False, indent=2))
        return 0

    import os

    token = (
        os.environ.get("PUBLIC_EVENT_GATEWAY_TOKEN")
        or os.environ.get("PUBLIC_EVENT_GATEWAY_API_TOKEN")
        or ""
    ).strip() or None
    url = args.api_base.rstrip("/") + "/api/public-events/ingest"
    try:
        result = _post_json(url, payload, token)
    except urllib.error.HTTPError as exc:
        err_body = exc.read().decode("utf-8", errors="replace")
        print(f"HTTP {exc.code}: {err_body}")
        return 1
    except urllib.error.URLError as exc:
        print(f"Request failed: {exc}")
        return 1

    print(json.dumps({"ok": True, "url": url, "result": result}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
