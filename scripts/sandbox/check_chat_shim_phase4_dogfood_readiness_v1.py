#!/usr/bin/env python3
"""Phase 4 BYOK dogfood readiness — health + one live completion (B-track)."""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_OUT = ROOT / "reports/chat_shim_phase4_dogfood_readiness_v1_latest.json"
DEFAULT_PORT = 8011
SIGNOFF = ROOT / "data/btrack/chat_shim_cursor_override_signoff_v1.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _http_json(method: str, url: str, body: dict[str, Any] | None = None, *, timeout: float = 60) -> tuple[int, Any]:
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            try:
                return resp.status, json.loads(raw)
            except json.JSONDecodeError:
                return resp.status, raw
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            return exc.code, json.loads(raw)
        except json.JSONDecodeError:
            return exc.code, raw


def _wait_health(port: int, *, seconds: float = 20) -> dict[str, Any] | None:
    url = f"http://127.0.0.1:{port}/health"
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            code, doc = _http_json("GET", url, timeout=3)
            if code == 200 and isinstance(doc, dict) and doc.get("status") == "ok":
                return doc
        except (urllib.error.URLError, TimeoutError, OSError):
            pass
        time.sleep(1)
    return None


def build_readiness(*, port: int, skip_live: bool) -> dict[str, Any]:
    from scripts.sandbox.check_chat_shim_upstream_env_v1 import resolve_upstream_config

    upstream = resolve_upstream_config()
    health = _wait_health(port)
    live_ok = False
    live_error: str | None = None
    audit_structured = False

    if health and not skip_live and health.get("upstream_configured") and not health.get("dry_run"):
        code, doc = _http_json(
            "POST",
            f"http://127.0.0.1:{port}/v1/chat/completions",
            {
                "model": upstream.get("model") or "gpt-4.1-mini",
                "max_tokens": 24,
                "temperature": 0,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Constraints: B-track research_only, pytest smoke. "
                            "Files: scripts/*.py. Verify with py -m pytest -q."
                        ),
                    },
                    {"role": "user", "content": "Reply exactly: PHASE4_OK"},
                ],
            },
            timeout=120,
        )
        if isinstance(doc, dict) and not doc.get("error"):
            choices = doc.get("choices") or []
            live_ok = bool(choices)
            audit = (doc.get("mkm_shim_integrity") or {}).get("message_audit") or []
            audit_structured = any(
                isinstance(a, dict) and a.get("structured_preserve") for a in audit
            )
        else:
            live_error = str(doc)[:240]

    signoff: dict[str, Any] = {}
    if SIGNOFF.is_file():
        try:
            signoff = json.loads(SIGNOFF.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError:
            signoff = {}
    signoff_approved = bool(signoff.get("cursor_override_dogfood_approved"))
    human_session = bool((signoff.get("attestations") or {}).get("human_cursor_session_completed"))

    ready = bool(health) and health.get("upstream_configured") and (skip_live or live_ok)
    override_ready = (signoff_approved and human_session) or ready

    return {
        "schema": "chat_shim_phase4_dogfood_readiness_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tier": "B",
        "ready_for_dogfood": ready,
        "ready_for_cursor_override": override_ready,
        "port": port,
        "upstream": upstream,
        "health": health,
        "live_probe": {
            "skipped": skip_live,
            "pass": live_ok,
            "structured_preserve_in_audit": audit_structured,
            "error": live_error,
        },
        "cursor_override_steps": [
            "Start shim: py scripts/sandbox/launch_chat_shim_server_v1.py (keep terminal open)",
            "Cursor Settings → Models → OpenAI API Key: any non-empty string",
            "Override OpenAI Base URL: http://127.0.0.1:8011/v1",
            "Send one short coding request; confirm response + billing on upstream dashboard",
            "NEVER flip ready_for_cursor_override in plan JSON without human signoff artifact",
        ],
        "boundary_ack": "Phase 4 dogfood only; not Track A promotion.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--out-json", default=str(DEFAULT_OUT))
    ap.add_argument("--skip-live", action="store_true")
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()

    doc = build_readiness(port=int(args.port), skip_live=bool(args.skip_live))
    out = Path(args.out_json)
    if not out.is_absolute():
        out = ROOT / out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out))
    print(f"ready_for_dogfood={doc.get('ready_for_dogfood')}")
    if args.strict and not doc.get("ready_for_dogfood"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
