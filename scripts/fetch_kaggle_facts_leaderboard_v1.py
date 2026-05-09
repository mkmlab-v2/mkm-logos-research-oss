#!/usr/bin/env python3
"""Fetch FACTS benchmark leaderboard from Kaggle benchmark API.

This does not require Kaggle CLI download endpoints. It uses the web API that
backs the public benchmark page and emits a normalized JSON artifact.
"""

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


def _session_headers(session: requests.Session) -> dict[str, str]:
    return {
        "x-xsrf-token": session.cookies.get("XSRF-TOKEN", ""),
        "x-csrf-token": session.cookies.get("CSRF-TOKEN", ""),
        "x-kaggle-client-token": session.cookies.get("CLIENT-TOKEN", ""),
        "content-type": "application/json",
    }


def _safe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _extract_metric(entry: dict[str, Any]) -> tuple[float | None, float | None]:
    runs = entry.get("runs") or []
    if not runs:
        return (None, None)
    results = (runs[0] or {}).get("results") or []
    if not results:
        return (None, None)
    numeric = (results[0] or {}).get("numericResult") or {}
    score = _safe_float(numeric.get("value"))
    ci = _safe_float(numeric.get("confidenceInterval"))
    return (score, ci)


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch Kaggle FACTS leaderboard snapshot.")
    parser.add_argument(
        "--out-json",
        type=Path,
        default=Path("docs/final/artifacts/facts_kaggle_leaderboard_latest.json"),
    )
    parser.add_argument("--timeout-sec", type=int, default=30)
    args = parser.parse_args()

    with requests.Session() as session:
        page = session.get(BENCHMARK_PAGE_URL, timeout=args.timeout_sec)
        page.raise_for_status()
        headers = _session_headers(session)

        benchmark_payload = {
            "benchmarkIdentifier": {
                "slugIdentifier": {"ownerSlug": "google", "benchmarkSlug": "facts"}
            }
        }
        benchmark_resp = session.post(
            GET_BENCHMARK_URL,
            json=benchmark_payload,
            headers=headers,
            timeout=args.timeout_sec,
        )
        benchmark_resp.raise_for_status()
        benchmark = benchmark_resp.json()
        benchmark_version_id = ((benchmark.get("version") or {}).get("id"))
        if benchmark_version_id is None:
            raise RuntimeError("Missing benchmark version id from Kaggle response")

        leaderboard_payload = {
            "versionIdentifier": {"versionIdSelector": {"id": benchmark_version_id}}
        }
        leaderboard_resp = session.post(
            GET_UNIFIED_LEADERBOARD_URL,
            json=leaderboard_payload,
            headers=headers,
            timeout=args.timeout_sec,
        )
        leaderboard_resp.raise_for_status()
        leaderboard = leaderboard_resp.json()

    task_headers = leaderboard.get("taskVersionHeaders") or []
    model_headers = leaderboard.get("modelVersionHeaders") or []
    entries = leaderboard.get("entries") or []

    task_name_by_id: dict[int, str] = {}
    for h in task_headers:
        tv = (h or {}).get("taskVersion") or {}
        tid = tv.get("id")
        name = tv.get("name")
        if isinstance(tid, int) and isinstance(name, str):
            task_name_by_id[tid] = name
        # Unified leaderboard often carries child benchmark versions in this array.
        bv = (h or {}).get("benchmarkVersion") or {}
        bvid = bv.get("id")
        bvname = bv.get("name")
        if isinstance(bvid, int) and isinstance(bvname, str):
            task_name_by_id[bvid] = bvname

    # Map leaf taskVersion ids (451,458,...) to suite pillar names using GetBenchmark child order
    # aligned with taskVersionHeaders rows that only have benchmarkVersion (Grounding, Multimodal, ...).
    suite_tv = (benchmark.get("version") or {}).get("taskVersion") or {}
    child_versions = suite_tv.get("childTaskVersions") or []
    child_ids: list[int] = []
    for cv in child_versions:
        cid = (cv or {}).get("id")
        if isinstance(cid, int):
            child_ids.append(cid)

    benchmark_only_headers: list[tuple[int, str]] = []
    for h in task_headers:
        hdr_tv = (h or {}).get("taskVersion") or {}
        hdr_bv = (h or {}).get("benchmarkVersion") or {}
        if hdr_tv.get("id") is None and isinstance(hdr_bv.get("id"), int):
            name = hdr_bv.get("name")
            if isinstance(name, str):
                benchmark_only_headers.append((hdr_bv["id"], name))

    if len(child_ids) == len(benchmark_only_headers):
        for cid, (_bid, pillar_name) in zip(child_ids, benchmark_only_headers, strict=True):
            task_name_by_id[cid] = pillar_name

    model_by_id: dict[int, dict[str, Any]] = {}
    for h in model_headers:
        mv = (h or {}).get("modelVersion") or {}
        vid = mv.get("id")
        if not isinstance(vid, int):
            continue
        model_by_id[vid] = {
            "rank": h.get("rank"),
            "medal": h.get("medal"),
            "display_name": mv.get("displayName"),
            "organization": ((mv.get("organization") or {}).get("name")),
            "slug": mv.get("slug"),
            "model_proxy_slug": mv.get("modelProxySlug"),
        }

    scores_by_model: dict[int, dict[str, Any]] = {}
    for entry in entries:
        model_id = entry.get("modelVersionId")
        task_id = entry.get("taskVersionId")
        if not isinstance(model_id, int) or not isinstance(task_id, int):
            continue
        score, ci = _extract_metric(entry)
        if model_id not in scores_by_model:
            scores_by_model[model_id] = {}
        task_name = task_name_by_id.get(task_id, f"task_{task_id}")
        scores_by_model[model_id][task_name] = {
            "score": score,
            "confidence_interval": ci,
        }

    models: list[dict[str, Any]] = []
    for model_id, meta in model_by_id.items():
        row = {
            "model_version_id": model_id,
            **meta,
            "scores": scores_by_model.get(model_id, {}),
        }
        models.append(row)

    models.sort(key=lambda x: (x.get("rank") is None, x.get("rank")))

    out = {
        "schema": "facts_kaggle_leaderboard_snapshot_v1",
        "generated_at_utc": _now_utc_iso(),
        "source": {
            "benchmark_page_url": BENCHMARK_PAGE_URL,
            "benchmark_name": benchmark.get("name"),
            "benchmark_slug": benchmark.get("slug"),
            "benchmark_id": benchmark.get("id"),
            "benchmark_version_id": benchmark_version_id,
        },
        "summary": {
            "task_count": len(task_name_by_id),
            "model_count": len(models),
            "entry_count": len(entries),
        },
        "tasks": task_name_by_id,
        "models": models,
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] wrote: {args.out_json}")
    print(
        "[SUMMARY] "
        f"models={out['summary']['model_count']}, "
        f"tasks={out['summary']['task_count']}, "
        f"entries={out['summary']['entry_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
