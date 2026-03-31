#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Any


def _safe_mean(vals: list[float]) -> float | None:
    return float(statistics.mean(vals)) if vals else None


def _safe_stdev(vals: list[float]) -> float | None:
    return float(statistics.stdev(vals)) if len(vals) >= 2 else 0.0 if vals else None


def _safe_min(vals: list[float]) -> float | None:
    return float(min(vals)) if vals else None


def _safe_max(vals: list[float]) -> float | None:
    return float(max(vals)) if vals else None


def _run_once(
    root: Path,
    dataset_jsonl: str,
    base_url: str,
    baseline_model: str,
    candidate_model: str,
    latency_max_delta_pct: float,
    quality_min_delta: float,
    out_json: Path,
) -> tuple[int, str, str]:
    cmd = [
        sys.executable,
        "scripts/run_vllm_ab_benchmark_template.py",
        "--dataset-jsonl",
        dataset_jsonl,
        "--baseline-url",
        base_url,
        "--candidate-url",
        base_url,
        "--baseline-model",
        baseline_model,
        "--candidate-model",
        candidate_model,
        "--usd-per-1k-tokens",
        "0",
        "--latency-max-delta-pct",
        str(latency_max_delta_pct),
        "--quality-min-delta",
        str(quality_min_delta),
        "--out-json",
        str(out_json),
    ]
    cp = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
    return cp.returncode, cp.stdout.strip(), cp.stderr.strip()


def main() -> int:
    ap = argparse.ArgumentParser(description="Repeat canary benchmark for baseline vs best candidate.")
    ap.add_argument("--base-url", default="http://127.0.0.1:8000")
    ap.add_argument("--dataset-jsonl", default="reports/constitution/btrack_pilot/vllm_ab_dataset_sample.jsonl")
    ap.add_argument("--baseline-model", default="mkm12-lite")
    ap.add_argument("--candidate-model", default="mkm12-accelerated")
    ap.add_argument("--runs", type=int, default=10)
    ap.add_argument("--latency-max-delta-pct", type=float, default=15.0)
    ap.add_argument("--quality-min-delta", type=float, default=0.0)
    ap.add_argument("--out-json", default="reports/constitution/btrack_pilot/vllm_ab_canary_repeat_latest.json")
    ap.add_argument(
        "--allow-unavailable",
        action="store_true",
        help="If vLLM endpoint is unavailable, write skipped report and exit 0",
    )
    args = ap.parse_args()

    root = Path(".").resolve()
    out = Path(args.out_json).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    try:
        with urllib.request.urlopen(args.base_url.rstrip("/") + "/v1/models", timeout=5):
            pass
    except Exception as e:
        if args.allow_unavailable:
            payload = {
                "schema": "vllm_ab_canary_repeat_v1",
                "base_url": args.base_url,
                "dataset_jsonl": str(Path(args.dataset_jsonl).resolve()),
                "baseline_model": args.baseline_model,
                "candidate_model": args.candidate_model,
                "skipped": True,
                "skip_reason": f"endpoint_unavailable: {e}",
                "summary": {"total_runs": 0, "valid_runs": 0, "go_count": 0, "go_rate": 0.0},
                "stable": False,
                "runs": [],
            }
            out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"WROTE: {out}")
            print("[vllm-canary-repeat] SKIP: endpoint unavailable")
            return 0
        raise

    run_rows: list[dict[str, Any]] = []
    for i in range(1, args.runs + 1):
        per_run_report = out.parent / f"vllm_ab_canary_run_{i:02d}.json"
        code, stdout, stderr = _run_once(
            root=root,
            dataset_jsonl=args.dataset_jsonl,
            base_url=args.base_url,
            baseline_model=args.baseline_model,
            candidate_model=args.candidate_model,
            latency_max_delta_pct=args.latency_max_delta_pct,
            quality_min_delta=args.quality_min_delta,
            out_json=per_run_report,
        )
        row: dict[str, Any] = {
            "run": i,
            "ok": code == 0,
            "returncode": code,
            "stdout": stdout,
            "stderr": stderr,
            "report_path": str(per_run_report),
        }
        if code == 0 and per_run_report.exists():
            payload = json.loads(per_run_report.read_text(encoding="utf-8"))
            row["go_no_go"] = payload.get("go_no_go")
            comp = payload.get("comparative") or {}
            row["p95_latency_delta_pct"] = comp.get("p95_latency_delta_pct")
            row["quality_delta"] = comp.get("quality_delta")
            cand = payload.get("candidate") or {}
            row["candidate_model_match_rate"] = cand.get("model_match_rate")
        run_rows.append(row)

    valid = [r for r in run_rows if r.get("ok") and r.get("go_no_go") in {"GO", "NO_GO"}]
    go_count = sum(1 for r in valid if r.get("go_no_go") == "GO")
    p95_deltas = [float(r["p95_latency_delta_pct"]) for r in valid if r.get("p95_latency_delta_pct") is not None]
    q_deltas = [float(r["quality_delta"]) for r in valid if r.get("quality_delta") is not None]

    summary = {
        "total_runs": args.runs,
        "valid_runs": len(valid),
        "go_count": go_count,
        "go_rate": (go_count / len(valid)) if valid else 0.0,
        "p95_latency_delta_pct": {
            "mean": _safe_mean(p95_deltas),
            "stdev": _safe_stdev(p95_deltas),
            "min": _safe_min(p95_deltas),
            "max": _safe_max(p95_deltas),
        },
        "quality_delta": {
            "mean": _safe_mean(q_deltas),
            "stdev": _safe_stdev(q_deltas),
            "min": _safe_min(q_deltas),
            "max": _safe_max(q_deltas),
        },
    }

    # Canary stability verdict: require 90%+ GO and no quality drop on mean.
    stable = summary["go_rate"] >= 0.9 and (summary["quality_delta"]["mean"] is None or summary["quality_delta"]["mean"] >= 0.0)

    payload = {
        "schema": "vllm_ab_canary_repeat_v1",
        "base_url": args.base_url,
        "dataset_jsonl": str(Path(args.dataset_jsonl).resolve()),
        "baseline_model": args.baseline_model,
        "candidate_model": args.candidate_model,
        "thresholds": {
            "latency_max_delta_pct": args.latency_max_delta_pct,
            "quality_min_delta": args.quality_min_delta,
            "stability_go_rate_min": 0.9,
        },
        "summary": summary,
        "stable": stable,
        "runs": run_rows,
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"WROTE: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
