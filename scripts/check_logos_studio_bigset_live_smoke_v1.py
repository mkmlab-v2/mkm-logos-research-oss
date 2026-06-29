#!/usr/bin/env python3
"""Live smoke: Logos Studio 50 presets + BigSet free-text queries on logos.jema-ai.com."""

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
DEFAULT_OUT = ROOT / "reports/logos_studio_bigset_live_smoke_v1_latest.json"
DEFAULT_BASE = "https://logos.jema-ai.com"

BIGSET_QUERIES: list[tuple[str, str]] = [
    ("nephilim_ko", "네피림이 뭐야?"),
    ("benei_en", "who are the sons of god in genesis 6"),
    ("watchers_ko", "감시자 watchers 전통"),
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _post_json(url: str, body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "MKM-LogosStudioBigsetSmoke/1.0",
            "Accept": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=45) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
        return int(resp.status), json.loads(raw)


def _get_json(url: str) -> tuple[int, dict[str, Any]]:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "MKM-LogosStudioBigsetSmoke/1.0", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=45) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
        return int(resp.status), json.loads(raw)


def run_smoke(base: str, *, min_presets: int) -> dict[str, Any]:
    failures: list[str] = []
    checks: dict[str, Any] = {"base": base.rstrip("/")}

    presets_url = f"{base.rstrip('/')}/api/logos-research/presets"
    query_url = f"{base.rstrip('/')}/api/logos-research/query"
    static_url = f"{base.rstrip('/')}/data/logos_studio/qa_presets_v1.json"

    try:
        code, presets_body = _get_json(presets_url)
        checks["presets_http"] = code
        preset_list = presets_body.get("presets") or []
        checks["api_preset_count"] = len(preset_list)
        bigset_ids = [p.get("id") for p in preset_list if str(p.get("id", "")).startswith("bigset_topic_")]
        checks["api_bigset_ids"] = bigset_ids
        if code != 200:
            failures.append(f"presets http {code}")
        if len(preset_list) < min_presets:
            failures.append(f"api preset_count {len(preset_list)} < {min_presets}")
        if len(bigset_ids) < 5:
            failures.append(f"api bigset presets {len(bigset_ids)} < 5")
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as e:
        failures.append(f"presets fetch failed: {e}")

    try:
        _, static_body = _get_json(static_url)
        static_count = len(static_body.get("presets") or [])
        checks["static_preset_count"] = static_count
        if static_count < min_presets:
            failures.append(f"static preset_count {static_count} < {min_presets}")
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as e:
        failures.append(f"static presets failed: {e}")

    query_results: dict[str, Any] = {}
    for key, query in BIGSET_QUERIES:
        try:
            code, body = _post_json(query_url, {"query": query})
            query_results[key] = {
                "http": code,
                "ok": body.get("ok"),
                "match": body.get("match"),
                "preset_id": (body.get("result") or {}).get("preset_id") or body.get("preset_id"),
                "error": body.get("error"),
            }
            if code != 200 or not body.get("ok"):
                failures.append(f"query {key}: http={code} error={body.get('error')}")
            elif not str(query_results[key]["preset_id"]).startswith("bigset_topic_"):
                failures.append(f"query {key}: expected bigset_topic_* got {query_results[key]['preset_id']}")
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as e:
            failures.append(f"query {key} failed: {e}")
            query_results[key] = {"error": str(e)}
    checks["queries"] = query_results

    ok = len(failures) == 0
    return {
        "schema": "logos_studio_bigset_live_smoke_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "ok": ok,
        "gate_pass": ok,
        "gate_failures": failures,
        "checks": checks,
        "reproducible_command": (
            f"py scripts/check_logos_studio_bigset_live_smoke_v1.py --base {base} --min-presets {min_presets}"
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", default=DEFAULT_BASE)
    ap.add_argument("--min-presets", type=int, default=50)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    doc = run_smoke(args.base, min_presets=args.min_presets)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["ok"], "gate_failures": doc["gate_failures"], "out": str(args.output)}, ensure_ascii=False))
    return 0 if doc["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
