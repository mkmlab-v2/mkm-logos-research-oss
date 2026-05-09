#!/usr/bin/env python3
"""Probe Kaggle FACTS submission channel feasibility.

Outputs a fact-lock artifact that answers:
- Is Kaggle token auth working?
- Does current kaggle Python SDK expose benchmark submission APIs?
- Do obvious BenchmarkService submission endpoints exist publicly?
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

import requests


def _now_utc_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _probe_kaggle_sdk() -> dict[str, Any]:
    out: dict[str, Any] = {
        "available": False,
        "authenticated": False,
        "version": None,
        "benchmark_methods": [],
        "competition_submissions_google_facts": None,
    }
    try:
        import kaggle
        from kaggle.api.kaggle_api_extended import KaggleApi
    except Exception as exc:
        out["error"] = f"import_failed: {exc}"
        return out

    out["available"] = True
    out["version"] = getattr(kaggle, "__version__", None)
    api = KaggleApi()
    try:
        api.authenticate()
        out["authenticated"] = True
    except Exception as exc:
        out["auth_error"] = str(exc)

    names = [n for n in dir(api) if "benchmark" in n.lower()]
    out["benchmark_methods"] = sorted(names)
    try:
        api.competition_submissions("google/facts")
        out["competition_submissions_google_facts"] = "ok"
    except Exception as exc:
        out["competition_submissions_google_facts"] = str(exc)
    return out


def _headers(session: requests.Session) -> dict[str, str]:
    return {
        "x-xsrf-token": session.cookies.get("XSRF-TOKEN", ""),
        "x-csrf-token": session.cookies.get("CSRF-TOKEN", ""),
        "x-kaggle-client-token": session.cookies.get("CLIENT-TOKEN", ""),
        "content-type": "application/json",
    }


def _probe_web_submission_candidates(timeout_sec: int) -> list[dict[str, Any]]:
    methods = [
        "CreateBenchmarkSubmission",
        "SubmitBenchmark",
        "SubmitBenchmarkVersion",
        "CreateSubmission",
        "UploadSubmission",
    ]
    probes: list[dict[str, Any]] = []
    with requests.Session() as s:
        s.get("https://www.kaggle.com/benchmarks/google/facts", timeout=timeout_sec)
        h = _headers(s)
        payload = {
            "benchmarkIdentifier": {"slugIdentifier": {"ownerSlug": "google", "benchmarkSlug": "facts"}}
        }
        for m in methods:
            url = f"https://www.kaggle.com/api/i/benchmarks.BenchmarkService/{m}"
            row: dict[str, Any] = {"method": m, "url": url}
            try:
                r = s.post(url, json=payload, headers=h, timeout=timeout_sec)
                row["status_code"] = r.status_code
                row["content_type"] = r.headers.get("content-type")
                row["body_preview"] = (r.text or "")[:180]
            except Exception as exc:
                row["error"] = str(exc)
            probes.append(row)
    return probes


def main() -> int:
    ap = argparse.ArgumentParser(description="Probe Kaggle FACTS submission channel")
    ap.add_argument(
        "--out-json",
        type=Path,
        default=Path("docs/final/artifacts/facts_submission_channel_probe_latest.json"),
    )
    ap.add_argument("--timeout-sec", type=int, default=25)
    args = ap.parse_args()

    sdk = _probe_kaggle_sdk()
    web = _probe_web_submission_candidates(args.timeout_sec)

    channel_open = bool(
        sdk.get("authenticated")
        and sdk.get("benchmark_methods")
        and any((p.get("status_code") or 0) < 400 for p in web)
    )
    out = {
        "schema": "facts_submission_channel_probe_v1",
        "generated_at_utc": _now_utc_iso(),
        "kaggle_sdk_probe": sdk,
        "benchmark_submission_endpoint_candidates": web,
        "submission_channel_open": channel_open,
        "assessment": (
            "open"
            if channel_open
            else "blocked_or_not_publicly_exposed_for_benchmarks"
        ),
        "next_action": (
            "If blocked: use Kaggle official benchmark submission mechanism when publicly documented/available; "
            "otherwise continue local eval + leaderboard alignment artifacts."
        ),
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] wrote: {args.out_json}")
    print(f"[SUMMARY] submission_channel_open={channel_open}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
