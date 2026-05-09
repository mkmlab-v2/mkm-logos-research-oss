#!/usr/bin/env python3
"""Probe public Kaggle FACTS benchmark APIs for official question access."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

import requests

BENCHMARK_PAGE_URL = "https://www.kaggle.com/benchmarks/google/facts"
GET_BENCHMARK_URL = "https://www.kaggle.com/api/i/benchmarks.BenchmarkService/GetBenchmark"
GET_UNIFIED_LEADERBOARD_URL = (
    "https://www.kaggle.com/api/i/benchmarks.BenchmarkService/GetUnifiedBenchmarkLeaderboard"
)


def _now_utc_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _headers(session: requests.Session) -> dict[str, str]:
    return {
        "x-xsrf-token": session.cookies.get("XSRF-TOKEN", ""),
        "x-csrf-token": session.cookies.get("CSRF-TOKEN", ""),
        "x-kaggle-client-token": session.cookies.get("CLIENT-TOKEN", ""),
        "content-type": "application/json",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Probe Kaggle FACTS official question accessibility")
    ap.add_argument(
        "--out-json",
        type=Path,
        default=Path("docs/final/artifacts/facts_official_access_probe_latest.json"),
    )
    ap.add_argument("--timeout-sec", type=int, default=30)
    args = ap.parse_args()

    result: dict[str, Any] = {
        "schema": "facts_official_access_probe_v1",
        "generated_at_utc": _now_utc_iso(),
        "benchmark_page_url": BENCHMARK_PAGE_URL,
        "official_examples_accessible": False,
        "notes": [],
    }

    with requests.Session() as s:
        page = s.get(BENCHMARK_PAGE_URL, timeout=args.timeout_sec)
        page.raise_for_status()
        h = _headers(s)

        b_payload = {
            "benchmarkIdentifier": {"slugIdentifier": {"ownerSlug": "google", "benchmarkSlug": "facts"}}
        }
        b_resp = s.post(GET_BENCHMARK_URL, json=b_payload, headers=h, timeout=args.timeout_sec)
        b_resp.raise_for_status()
        bench = b_resp.json()
        version_id = ((bench.get("version") or {}).get("id"))
        result["benchmark"] = {
            "id": bench.get("id"),
            "slug": bench.get("slug"),
            "version_id": version_id,
            "name": bench.get("name"),
        }
        result["task_version_keys"] = list(((bench.get("version") or {}).get("taskVersion") or {}).keys())

        lb_resp = s.post(
            GET_UNIFIED_LEADERBOARD_URL,
            json={"versionIdentifier": {"versionIdSelector": {"id": version_id}}},
            headers=h,
            timeout=args.timeout_sec,
        )
        lb_resp.raise_for_status()
        lb = lb_resp.json()
        result["leaderboard_summary"] = {
            "model_headers": len(lb.get("modelVersionHeaders") or []),
            "task_headers": len(lb.get("taskVersionHeaders") or []),
            "entries": len(lb.get("entries") or []),
        }

    # Public API payloads above do not include question text/examples.
    result["notes"].append(
        "GetBenchmark/GetUnifiedBenchmarkLeaderboard are accessible, but provide metadata/scores only."
    )
    result["notes"].append(
        "No public question/example payload was found through these endpoints; official full testset run remains blocked."
    )
    result["next_action"] = (
        "Use official Kaggle submission/evaluation channel (if/when API or hosted runner is exposed) "
        "or keep current mode: local protocol eval + Kaggle leaderboard alignment."
    )

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] wrote: {args.out_json}")
    print("[SUMMARY] official_examples_accessible=False (metadata+leaderboard only)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
