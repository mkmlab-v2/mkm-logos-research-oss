#!/usr/bin/env python3
"""
HTTP load probe for token compression stub (§9.2 bench path).

- Measures client-observed latencies (p50/p95/p99/max) and error rate.
- Peak RSS: optional psutil on --server-pid (same host) or this process only (--rss-self).
  Server RSS from a remote client is NOT measurable here; record "not_measured" unless PID given.

Usage (stub must be running, e.g. uvicorn on 8010):
  py scripts/bench_l1_api_load.py --base-url http://127.0.0.1:8010

Dry-run (no network; writes schema shell):
  py scripts/bench_l1_api_load.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "bench_l1_api_load_latest.json"
SCHEMA = "bench_l1_api_load_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _git_head_short() -> str | None:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=5,
        )
        return out.strip()[:12] or None
    except (subprocess.CalledProcessError, OSError, subprocess.TimeoutExpired):
        return None


def _percentile_ms(latencies_ms: list[float], p: float) -> float | None:
    if not latencies_ms:
        return None
    s = sorted(latencies_ms)
    if len(s) == 1:
        return s[0]
    k = (len(s) - 1) * (p / 100.0)
    f = int(math.floor(k))
    c = min(f + 1, len(s) - 1)
    d = k - f
    return s[f] + (s[c] - s[f]) * d


def _rss_bytes_pid(pid: int) -> int | None:
    try:
        import psutil  # type: ignore[import-untyped]
    except ImportError:
        return None
    try:
        return int(psutil.Process(pid).memory_info().rss)
    except (psutil.Error, ValueError):
        return None


def _rss_bytes_self() -> int | None:
    return _rss_bytes_pid(os.getpid())


def _one_post(url: str, body: bytes, timeout: float) -> tuple[str, float]:
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            resp.read()
        return "ok", (time.perf_counter() - t0) * 1000.0
    except urllib.error.HTTPError as e:
        e.read()
        return f"http_{e.code}", (time.perf_counter() - t0) * 1000.0
    except Exception:
        return "error", (time.perf_counter() - t0) * 1000.0


def run_bench(
    base_url: str,
    path: str,
    total_requests: int,
    max_concurrent: int,
    approx_words: int,
    timeout: float,
    server_pid: int | None,
    rss_self: bool,
    mkm_user_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    url = base_url.rstrip("/") + path
    stem = "benchw "
    text = (stem * approx_words).strip()
    payload_template: dict[str, Any] = {
        "text": text,
        "client_request_id": "bench-{i}",
    }
    if mkm_user_context:
        payload_template["mkm_user_context"] = mkm_user_context
    latencies_ok: list[float] = []
    latencies_err: list[float] = []
    status_counts: dict[str, int] = {}

    def job(i: int) -> None:
        body = json.dumps(
            {**payload_template, "client_request_id": f"bench-{i}"},
            ensure_ascii=False,
        ).encode("utf-8")
        st, ms = _one_post(url, body, timeout)
        status_counts[st] = status_counts.get(st, 0) + 1
        if st == "ok":
            latencies_ok.append(ms)
        else:
            latencies_err.append(ms)

    rss_before: int | None = None
    if server_pid:
        rss_before = _rss_bytes_pid(server_pid)
    elif rss_self:
        rss_before = _rss_bytes_self()

    t_wall0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=max(1, max_concurrent)) as ex:
        futures = [ex.submit(job, i) for i in range(total_requests)]
        for fut in futures:
            fut.result()
    wall_s = time.perf_counter() - t_wall0

    rss_after: int | None = None
    if server_pid:
        rss_after = _rss_bytes_pid(server_pid)
    elif rss_self:
        rss_after = _rss_bytes_self()

    all_lat = latencies_ok + latencies_err
    ok_n = len(latencies_ok)
    err_n = total_requests - ok_n

    out: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "draft_benchmark": True,
        "notes": (
            "Latencies are client-observed RTT. "
            "server_rss_bytes_* require --server-pid on same host with psutil installed."
        ),
        "base_url": base_url,
        "path": path,
        "total_requests": total_requests,
        "max_concurrent": max_concurrent,
        "approx_word_tokens": approx_words,
        "wall_time_s": round(wall_s, 4),
        "ok_count": ok_n,
        "error_count": err_n,
        "error_rate": round(err_n / total_requests, 6) if total_requests else None,
        "status_counts": status_counts,
        "latency_ms": {
            "p50": round(_percentile_ms(latencies_ok, 50) or 0, 3)
            if latencies_ok
            else None,
            "p95": round(_percentile_ms(latencies_ok, 95) or 0, 3)
            if latencies_ok
            else None,
            "p99": round(_percentile_ms(latencies_ok, 99) or 0, 3)
            if latencies_ok
            else None,
            "max": round(max(latencies_ok), 3) if latencies_ok else None,
        },
        "latency_ms_including_errors_p95": round(_percentile_ms(all_lat, 95) or 0, 3)
        if all_lat
        else None,
        "server_pid": server_pid,
        "rss_self_sampled": rss_self,
        "server_rss_bytes_before": rss_before,
        "server_rss_bytes_after": rss_after,
        "command_fingerprint": {
            "bench_script": "scripts/bench_l1_api_load.py",
            "git_commit": _git_head_short(),
            "mkm_user_context_included": bool(mkm_user_context),
        },
        "draft_targets_comparison": {
            "p95_target_ms": 200,
            "rss_target_bytes": int(2.5 * 1024**3),
            "infra_ram_draft_gb": 8,
            "pass_p95_vs_target": None,
            "pass_rss_vs_target": None,
        },
    }
    if latencies_ok and out["latency_ms"]["p95"] is not None:
        out["draft_targets_comparison"]["pass_p95_vs_target"] = (
            out["latency_ms"]["p95"] <= 200.0
        )
    if rss_after is not None:
        out["draft_targets_comparison"]["pass_rss_vs_target"] = rss_after <= int(
            2.5 * 1024**3
        )
    return out


def main() -> int:
    p = argparse.ArgumentParser(description="L1/stub HTTP load bench (§9.2)")
    p.add_argument("--base-url", default="http://127.0.0.1:8010")
    p.add_argument("--path", default="/v1/compress")
    p.add_argument("--total-requests", type=int, default=100)
    p.add_argument("--max-concurrent", type=int, default=10)
    p.add_argument("--approx-words", type=int, default=1000)
    p.add_argument("--timeout", type=float, default=60.0)
    p.add_argument("--server-pid", type=int, default=0, help="Same-host stub PID for RSS sample")
    p.add_argument(
        "--rss-self",
        action="store_true",
        help="Sample this bench process RSS only (not the API server)",
    )
    p.add_argument("--out", type=Path, default=DEFAULT_OUT)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument(
        "--mkm-user-context-json",
        type=Path,
        default=None,
        help="Optional MKM_User_Context_v1 JSON file merged into each compress payload (load test parity).",
    )
    args = p.parse_args()
    server_pid = args.server_pid if args.server_pid > 0 else None

    mkm_uc: dict[str, Any] | None = None
    if args.mkm_user_context_json:
        raw = args.mkm_user_context_json.read_text(encoding="utf-8")
        loaded = json.loads(raw)
        if not isinstance(loaded, dict):
            print(json.dumps({"ok": False, "error": "mkm_user_context_json must be a JSON object"}))
            return 2
        mkm_uc = loaded

    if args.dry_run:
        payload = {
            "schema": SCHEMA,
            "generated_at_utc": _utc_now(),
            "research_only": True,
            "draft_benchmark": True,
            "dry_run": True,
            "message": "No HTTP requests executed; stub not contacted.",
            "mkm_user_context_included": bool(mkm_uc),
        }
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(json.dumps({"ok": True, "out": str(args.out), "dry_run": True}))
        return 0

    data = run_bench(
        args.base_url,
        args.path,
        args.total_requests,
        args.max_concurrent,
        args.approx_words,
        args.timeout,
        server_pid,
        args.rss_self,
        mkm_user_context=mkm_uc,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"ok": True, "out": str(args.out), "error_rate": data.get("error_rate")}))
    return 0 if data.get("error_count", 0) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
