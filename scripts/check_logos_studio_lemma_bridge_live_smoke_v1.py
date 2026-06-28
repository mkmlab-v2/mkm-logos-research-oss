#!/usr/bin/env python3
"""Live smoke: Logos Studio lemma bridge on logos.jema-ai.com.

Reproduce:
  py scripts/check_logos_studio_lemma_bridge_live_smoke_v1.py
  py scripts/check_logos_studio_lemma_bridge_live_smoke_v1.py --base https://logos.jema-ai.com --timeout-s 180
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/logos_studio_lemma_bridge_live_smoke_v1_latest.json"
DEFAULT_BASE = "https://logos.jema-ai.com"

CASES: list[dict[str, Any]] = [
    {
        "id": "nephilim_lemma_bridge",
        "body": {"query": "nephilim giants genesis 6"},
        "expect_mode_contains": "lemma_bridge",
        "min_neighbors": 1,
        "timeout_s": 180,
    },
    {
        "id": "psalm_graphrag_lemma_bridge",
        "body": {"query": "소망과 인내 시편"},
        "expect_mode_contains": "lemma_bridge",
        "min_neighbors": 1,
        "timeout_s": 180,
    },
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _post_json(url: str, body: dict[str, Any], *, timeout_s: int) -> tuple[int, dict[str, Any]]:
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "MKM-LogosLemmaBridgeLiveSmoke/1.0",
            "Accept": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
        return int(resp.status), json.loads(raw)


def run_smoke(base: str, *, default_timeout_s: int) -> dict[str, Any]:
    failures: list[str] = []
    query_url = f"{base.rstrip('/')}/api/logos-research/query"
    results: dict[str, Any] = {}

    for case in CASES:
        cid = case["id"]
        timeout_s = int(case.get("timeout_s") or default_timeout_s)
        try:
            code, body = _post_json(query_url, case["body"], timeout_s=timeout_s)
            result = body.get("result") or {}
            mode = str(result.get("query_mode") or "")
            meta = result.get("lemma_bridge_meta") or {}
            neighbors = int(meta.get("neighbor_count") or 0)
            row = {
                "http": code,
                "ok": body.get("ok"),
                "query_mode": mode,
                "neighbor_count": neighbors,
                "synthesis_mode": meta.get("synthesis_mode"),
                "error": body.get("error"),
            }
            results[cid] = row
            if code != 200 or not body.get("ok"):
                failures.append(f"{cid}: http={code} error={body.get('error')}")
            elif case["expect_mode_contains"] not in mode:
                failures.append(f"{cid}: query_mode missing {case['expect_mode_contains']} got {mode}")
            elif neighbors < int(case["min_neighbors"]):
                failures.append(f"{cid}: neighbor_count {neighbors} < {case['min_neighbors']}")
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as e:
            failures.append(f"{cid}: {e}")
            results[cid] = {"error": str(e)}

    ok = not failures
    return {
        "schema": "logos_studio_lemma_bridge_live_smoke_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "base": base.rstrip("/"),
        "ok": ok,
        "gate_failures": failures,
        "cases": results,
        "reproduce": f"py scripts/check_logos_studio_lemma_bridge_live_smoke_v1.py --base {base}",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", default=DEFAULT_BASE)
    ap.add_argument("--timeout-s", type=int, default=120)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    doc = run_smoke(args.base, default_timeout_s=args.timeout_s)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["ok"], "gate_failures": doc["gate_failures"], "out": str(args.output)}, ensure_ascii=False))
    return 0 if doc["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
