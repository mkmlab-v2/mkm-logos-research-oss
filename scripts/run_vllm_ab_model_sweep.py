#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Any


def _fetch_models(base_url: str) -> list[str]:
    url = base_url.rstrip("/") + "/v1/models"
    with urllib.request.urlopen(url, timeout=10) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    data = payload.get("data") or []
    return [str(x.get("id")) for x in data if x.get("id")]


def _run_one(
    root: Path,
    dataset_jsonl: str,
    base_url: str,
    baseline_model: str,
    candidate_model: str,
    out_json: Path,
    latency_max_delta_pct: float,
    quality_min_delta: float,
) -> dict[str, Any]:
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
    result: dict[str, Any] = {
        "candidate_model": candidate_model,
        "ok": cp.returncode == 0,
        "returncode": cp.returncode,
        "stdout": cp.stdout.strip(),
        "stderr": cp.stderr.strip(),
    }
    if cp.returncode != 0 or not out_json.exists():
        return result
    payload = json.loads(out_json.read_text(encoding="utf-8"))
    comp = payload.get("comparative") or {}
    cand = payload.get("candidate") or {}
    result.update(
        {
            "go_no_go": payload.get("go_no_go"),
            "p95_latency_delta_pct": comp.get("p95_latency_delta_pct"),
            "quality_delta": comp.get("quality_delta"),
            "candidate_model_match_rate": cand.get("model_match_rate"),
            "report_path": str(out_json),
        }
    )
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description="Run mini sweep of local vLLM/OpenAI-compatible models.")
    ap.add_argument("--base-url", default="http://127.0.0.1:8000")
    ap.add_argument("--dataset-jsonl", default="reports/constitution/btrack_pilot/vllm_ab_dataset_sample.jsonl")
    ap.add_argument("--baseline-model", default="mkm12-lite")
    ap.add_argument("--candidates", nargs="*", default=[])
    ap.add_argument("--latency-max-delta-pct", type=float, default=15.0)
    ap.add_argument("--quality-min-delta", type=float, default=0.0)
    ap.add_argument("--out-json", default="reports/constitution/btrack_pilot/vllm_ab_model_sweep_latest.json")
    args = ap.parse_args()

    root = Path(".").resolve()
    out = Path(args.out_json).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    all_models = _fetch_models(args.base_url)
    candidates = args.candidates or [m for m in all_models if m != args.baseline_model]

    rows: list[dict[str, Any]] = []
    for candidate in candidates:
        per_out = out.parent / f"vllm_ab_{args.baseline_model}_vs_{candidate}.json"
        row = _run_one(
            root=root,
            dataset_jsonl=args.dataset_jsonl,
            base_url=args.base_url,
            baseline_model=args.baseline_model,
            candidate_model=candidate,
            out_json=per_out,
            latency_max_delta_pct=args.latency_max_delta_pct,
            quality_min_delta=args.quality_min_delta,
        )
        rows.append(row)

    go_rows = [r for r in rows if r.get("ok") and r.get("go_no_go") == "GO"]
    go_rows_sorted = sorted(go_rows, key=lambda r: float(r.get("p95_latency_delta_pct", 10**9)))
    best = go_rows_sorted[0] if go_rows_sorted else None

    payload = {
        "schema": "vllm_ab_model_sweep_v1",
        "base_url": args.base_url,
        "baseline_model": args.baseline_model,
        "dataset_jsonl": str(Path(args.dataset_jsonl).resolve()),
        "models_discovered": all_models,
        "candidates_evaluated": candidates,
        "results": rows,
        "best_candidate": best,
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"WROTE: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
