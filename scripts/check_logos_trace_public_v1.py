#!/usr/bin/env python3
"""Smoke: public Logos Trace API (api.jemaai.cloud) + local fallback."""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PUBLIC = "https://api.jemaai.cloud/v1/logos/health"
DEFAULT_LOCAL = "http://127.0.0.1:8021/health"


def _get(url: str, timeout: float) -> tuple[int, dict]:
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (compatible; MKM-LogosTraceCheck/1.0)",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            return e.code, json.loads(raw)
        except json.JSONDecodeError:
            return e.code, {"error": raw[:200]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--public-url", default=DEFAULT_PUBLIC)
    ap.add_argument("--local-url", default=DEFAULT_LOCAL)
    ap.add_argument("--timeout", type=float, default=15.0)
    ap.add_argument("--out-json", type=Path, default=ROOT / "reports/logos_trace_public_check_v1_latest.json")
    args = ap.parse_args()

    results: dict = {"checks": []}
    ok = True
    for label, url in (("public", args.public_url), ("local", args.local_url)):
        try:
            code, doc = _get(url, args.timeout)
            passed = code == 200 and bool(doc.get("ok"))
            results["checks"].append({"label": label, "url": url, "status": code, "ok": passed, "body": doc})
            if not passed:
                ok = False
        except Exception as exc:  # noqa: BLE001
            results["checks"].append({"label": label, "url": url, "ok": False, "error": str(exc)})
            ok = False

    results["ok"] = ok
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
