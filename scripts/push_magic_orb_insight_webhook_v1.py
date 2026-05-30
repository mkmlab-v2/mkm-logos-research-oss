#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""POST magic_orb_question_insight_v1 to mkmlife insight webhook (KV warm, local dev)."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INSIGHT = ROOT / "docs/final/artifacts/magic_orb_question_insight_v1_latest.json"


def _load(path: Path) -> dict[str, Any]:
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    if doc.get("schema") != "magic_orb_question_insight_v1":
        raise SystemExit(f"expected magic_orb_question_insight_v1: {path}")
    return doc


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--insight-json", type=Path, default=DEFAULT_INSIGHT)
    ap.add_argument(
        "--base-url",
        default=os.environ.get("MKMLIFE_BASE_URL", "http://127.0.0.1:3105"),
        help="mkmlife dev origin (no trailing slash)",
    )
    ap.add_argument("--query", default="", help="override query field in POST body")
    ap.add_argument("--skip-latest", action="store_true", help="pass skip_latest to API")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument(
        "--push-all-by-query",
        action="store_true",
        help="POST each public/data/magic_orb_insight_by_query/*.json",
    )
    args = ap.parse_args()

    by_query_dir = ROOT / "projects/mkm/mkm-life/public/data/magic_orb_insight_by_query"
    paths: list[Path] = []
    if args.push_all_by_query and by_query_dir.is_dir():
        paths = sorted(by_query_dir.glob("*.json"))
    else:
        p = args.insight_json if args.insight_json.is_absolute() else ROOT / args.insight_json
        paths = [p]

    token = os.environ.get("MKM_MAGIC_ORB_INSIGHT_WEBHOOK_TOKEN", "").strip()
    if not token and not args.dry_run:
        print(
            "MKM_MAGIC_ORB_INSIGHT_WEBHOOK_TOKEN unset; POST will 401 unless route allows open dev.",
            file=sys.stderr,
        )

    url = f"{args.base_url.rstrip('/')}/api/v1/magic-orb/insight"
    results: list[dict[str, Any]] = []
    rc = 0

    for path in paths:
        doc = _load(path)
        body: dict[str, Any] = {
            "payload": doc,
            "query": (args.query or doc.get("query") or "").strip(),
        }
        if args.skip_latest:
            body["skip_latest"] = True

        if args.dry_run:
            gb = doc.get("graph_bloom") or {}
            n = len(gb.get("nodes") or [])
            results.append({"file": str(path.name), "dry_run": True, "graph_bloom_nodes": n})
            continue

        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            method="POST",
            headers={
                "Content-Type": "application/json",
                **({"x-mkm-insight-token": token} if token else {}),
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                out = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            print(f"HTTP {e.code} {path.name}: {err_body}", file=sys.stderr)
            rc = 1
            continue

        if not out.get("ok"):
            print(json.dumps({"file": path.name, **out}, ensure_ascii=False), file=sys.stderr)
            rc = 1
            continue
        results.append(
            {
                "file": path.name,
                "ok": True,
                "storage": out.get("storage"),
                "cache_key": out.get("cache_key"),
            }
        )

    print(json.dumps({"ok": rc == 0, "count": len(results), "results": results}, ensure_ascii=False))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
