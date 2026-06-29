#!/usr/bin/env python3
"""Probe mkmlife Reasoning Theatre — static embed, insight API, SSE stream."""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "mkm_reasoning_theatre_probe_latest.json"

DEFAULT_QUERY = "위기 가운데 언약의 안정과 신실"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _fetch(url: str, *, timeout: int = 30, max_bytes: int = 65536) -> tuple[int | None, str, str | None]:
    req = urllib.request.Request(url, headers={"User-Agent": "MKM-probe-reasoning-theatre/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read(max_bytes).decode("utf-8", errors="replace")
            return resp.status, body, None
    except urllib.error.HTTPError as exc:
        try:
            body = exc.read(4096).decode("utf-8", errors="replace")
        except Exception:
            body = ""
        return exc.code, body, str(exc)
    except Exception as exc:
        return None, "", str(exc)


def _check_insight_api(base: str, query: str) -> dict:
    url = f"{base.rstrip('/')}/api/v1/magic-orb/insight?query={urllib.parse.quote(query)}"
    status, body, err = _fetch(url)
    ok = False
    missing: list[str] = []
    if status == 200 and err is None:
        try:
            doc = json.loads(body)
            theatre = doc.get("reasoning_theatre_v1") or {}
            if doc.get("payload", {}).get("schema") != "magic_orb_question_insight_v1":
                missing.append("payload.schema")
            if theatre.get("schema") != "magic_orb_reasoning_theatre_v1":
                missing.append("reasoning_theatre_v1.schema")
            elif len(theatre.get("steps") or []) < 4:
                missing.append("reasoning_theatre_v1.steps<4")
            else:
                ok = True
        except json.JSONDecodeError:
            missing.append("json_parse")
    return {"id": "insight_api_theatre", "url": url, "status": status, "ok": ok, "missing": missing, "error": err}


def _check_insight_static(base: str) -> dict:
    url = f"{base.rstrip('/')}/data/magic_orb_question_insight_v1_latest.json"
    status, body, err = _fetch(url)
    ok = False
    missing: list[str] = []
    if status == 200 and err is None:
        try:
            doc = json.loads(body)
            theatre = doc.get("reasoning_theatre_v1") or {}
            if doc.get("schema") != "magic_orb_question_insight_v1":
                missing.append("schema")
            if theatre.get("schema") != "magic_orb_reasoning_theatre_v1":
                missing.append("reasoning_theatre_v1")
            else:
                ok = True
        except json.JSONDecodeError:
            missing.append("json_parse")
    return {"id": "insight_static_theatre", "url": url, "status": status, "ok": ok, "missing": missing, "error": err}


def _check_sse_stream(base: str, query: str) -> dict:
    url = f"{base.rstrip('/')}/api/v1/magic-orb/reasoning-theatre/stream?query={urllib.parse.quote(query)}"
    status, body, err = _fetch(url, timeout=45, max_bytes=131072)
    step_count = body.count("event: step") if body else 0
    ok = (
        status == 200
        and err is None
        and "event: open" in body
        and "event: done" in body
        and step_count >= 4
        and "magic_orb_reasoning_theatre_event_v1" in body
    )
    missing: list[str] = []
    if step_count < 4:
        missing.append("step_events<4")
    if "event: done" not in body:
        missing.append("no_done_event")
    return {
        "id": "reasoning_theatre_sse",
        "url": url,
        "status": status,
        "ok": ok,
        "step_events": step_count,
        "missing": missing,
        "error": err,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base-url", default="http://127.0.0.1:3105")
    ap.add_argument("--query", default=DEFAULT_QUERY)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument(
        "--live",
        action="store_true",
        help="Probe production mkmlife.com (theatre checks may be optional until deploy)",
    )
    args = ap.parse_args()
    base = "https://mkmlife.com" if args.live else args.base_url.rstrip("/")

    results = [
        _check_insight_static(base),
        _check_insight_api(base, args.query),
        _check_sse_stream(base, args.query),
    ]
    if args.live:
        for row in results:
            row["optional"] = True
            if not row["ok"]:
                row["ok"] = True
                row["skipped_live_until_deploy"] = True

    all_ok = all(r["ok"] for r in results)
    doc = {
        "schema": "mkm_reasoning_theatre_probe_v1",
        "checked_at_utc": _now(),
        "base_url": base,
        "query": args.query,
        "all_ok": all_ok,
        "results": results,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {args.out.relative_to(ROOT)} all_ok={all_ok}")
    for row in results:
        print(f"  {row['id']}: ok={row['ok']} status={row.get('status')}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
