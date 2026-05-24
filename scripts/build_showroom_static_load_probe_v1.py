#!/usr/bin/env python3
"""Low-rate public static URL load probe (P2 infra smoke, not media-scale stress)."""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports" / "showroom_static_load_probe_v1_latest.json"

URLS = [
    "https://jemaai.cloud/showroom_logos_chronology_overlay_v1.json",
    "https://jemaai.cloud/public_showroom_logos_oracle_v6.html",
    "https://api.jemaai.cloud/showroom_trust_visualization_slice_v0.json",
]


def _fetch(url: str, timeout: float) -> dict:
    t0 = time.perf_counter()
    req = urllib.request.Request(url, method="GET")
    req.add_header("User-Agent", "mkm-showroom-static-load-probe/1")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            _ = resp.read(65536)
            ms = (time.perf_counter() - t0) * 1000.0
            return {"url": url, "ok": resp.status == 200, "status": resp.status, "latency_ms": round(ms, 2)}
    except urllib.error.HTTPError as e:
        ms = (time.perf_counter() - t0) * 1000.0
        return {"url": url, "ok": False, "status": e.code, "latency_ms": round(ms, 2), "error": str(e)}
    except Exception as e:
        ms = (time.perf_counter() - t0) * 1000.0
        return {"url": url, "ok": False, "status": None, "latency_ms": round(ms, 2), "error": str(e)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--requests-per-url", type=int, default=30)
    ap.add_argument("--timeout", type=float, default=15.0)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    jobs = [u for u in URLS for _ in range(max(1, args.requests_per_url))]
    results: list[dict] = []
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as ex:
        futs = [ex.submit(_fetch, url, args.timeout) for url in jobs]
        for fut in as_completed(futs):
            results.append(fut.result())

    ok_n = sum(1 for r in results if r.get("ok"))
    latencies = [r["latency_ms"] for r in results if r.get("ok") and r.get("latency_ms") is not None]
    doc = {
        "schema": "showroom_static_load_probe_v1",
        "checked_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "policy": {
            "research_only": True,
            "not_media_scale": True,
            "note": "Low-rate probe only; does not prove 10k RPS capacity.",
        },
        "config": {
            "workers": args.workers,
            "requests_per_url": args.requests_per_url,
            "total_requests": len(jobs),
            "urls": URLS,
        },
        "summary": {
            "ok_rate": round(ok_n / len(results), 6) if results else 0.0,
            "ok_count": ok_n,
            "fail_count": len(results) - ok_n,
            "latency_ms_p50": round(statistics.median(latencies), 2) if latencies else None,
            "latency_ms_p95": round(sorted(latencies)[int(0.95 * (len(latencies) - 1))], 2) if len(latencies) >= 2 else (latencies[0] if latencies else None),
        },
        "results_sample": results[:12],
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["summary"]["fail_count"] == 0, "summary": doc["summary"]}, ensure_ascii=False))
    return 0 if doc["summary"]["fail_count"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
