#!/usr/bin/env python3
"""Live marker check for Logos Magic Orb q04/q08 static JSON (B-track closure)."""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request

UA = {"User-Agent": "MKM-logos-quality-lane-closure/1.0"}
MAX_BYTES = 524288


def _fetch(url: str) -> tuple[int | None, str, str | None]:
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            return resp.status, resp.read(MAX_BYTES).decode("utf-8", "replace"), None
    except urllib.error.HTTPError as exc:
        try:
            body = exc.read(2048).decode("utf-8", errors="replace")
        except Exception:
            body = ""
        return exc.code, body, str(exc)
    except Exception as exc:
        return None, "", str(exc)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--q04-hash", required=True)
    parser.add_argument("--q08-hash", required=True)
    parser.add_argument("--bridge-marker", required=True)
    args = parser.parse_args()

    checks = {
        "q04": {
            "url": f"https://mkmlife.com/data/magic_orb_insight_by_query/{args.q04_hash}.json",
            "expect_query_id": "q04",
            "body_marker": args.bridge_marker,
        },
        "q08": {
            "url": f"https://mkmlife.com/data/magic_orb_insight_by_query/{args.q08_hash}.json",
            "expect_query_id": "q08",
            "body_marker": None,
        },
    }

    out: dict[str, dict] = {}
    for qid, spec in checks.items():
        status, body, err = _fetch(spec["url"])
        marker_ok = False
        query_id = None
        if err is None and body:
            try:
                doc = json.loads(body)
                query_id = doc.get("query_id")
            except json.JSONDecodeError:
                query_id = None
            id_ok = query_id == spec["expect_query_id"]
            bridge_ok = True
            if spec["body_marker"]:
                bridge_ok = spec["body_marker"] in body
            marker_ok = id_ok and bridge_ok and status is not None and 200 <= status < 400
        out[qid] = {
            "url": spec["url"],
            "marker_ok": marker_ok,
            "status": status,
            "query_id": query_id,
            "error": err,
        }

    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
