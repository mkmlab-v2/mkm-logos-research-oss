#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import statistics
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class EvalRow:
    case_id: str
    lane: str
    ok: bool
    latency_ms: float
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None
    cost_estimate_usd: float | None
    output_text: str
    response_model: str | None
    expected_model: str
    model_match: bool | None
    quality_pass: bool | None
    error: str | None


def _write_sample_dataset(path: Path) -> None:
    rows = [
        {
            "id": "case_001",
            "messages": [
                {"role": "system", "content": "You are a concise assistant."},
                {"role": "user", "content": "Summarize why strict grounding reduces hallucination in one sentence."},
            ],
            "expected_substrings": ["ground", "halluc"],
        },
        {
            "id": "case_002",
            "messages": [
                {"role": "system", "content": "You are a concise assistant."},
                {"role": "user", "content": "Return exactly three bullet points on latency optimization."},
            ],
            "expected_substrings": ["latency"],
        },
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def _post_chat(url: str, model: str, messages: list[dict[str, str]], temperature: float, max_tokens: int) -> tuple[dict[str, Any], float]:
    body = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url=url.rstrip("/") + "/v1/chat/completions",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=120) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    return payload, elapsed_ms


def _extract_text(payload: dict[str, Any]) -> str:
    choices = payload.get("choices") or []
    if not choices:
        return ""
    msg = choices[0].get("message") or {}
    return str(msg.get("content") or "")


def _contains_all(text: str, needles: list[str]) -> bool:
    lower = text.lower()
    return all(n.lower() in lower for n in needles)


def _calc_cost(total_tokens: int | None, usd_per_1k_tokens: float) -> float | None:
    if total_tokens is None:
        return None
    return (float(total_tokens) / 1000.0) * usd_per_1k_tokens


def _p95(vals: list[float]) -> float:
    if not vals:
        return 0.0
    s = sorted(vals)
    # Nearest-rank percentile; for n=2 this selects max value.
    idx = max(0, min(len(s) - 1, math.ceil(len(s) * 0.95) - 1))
    return s[idx]


def _lane_stats(rows: list[EvalRow]) -> dict[str, Any]:
    lat = [r.latency_ms for r in rows if r.ok]
    costs = [r.cost_estimate_usd for r in rows if r.cost_estimate_usd is not None]
    quality_rows = [r for r in rows if r.quality_pass is not None]
    quality_passes = [r for r in quality_rows if r.quality_pass]
    model_rows = [r for r in rows if r.model_match is not None]
    model_matches = [r for r in model_rows if r.model_match]
    error_rows = [r for r in rows if not r.ok]
    return {
        "count": len(rows),
        "success_count": len(rows) - len(error_rows),
        "error_count": len(error_rows),
        "mean_latency_ms": round(statistics.mean(lat), 3) if lat else None,
        "p95_latency_ms": round(_p95(lat), 3) if lat else None,
        "mean_cost_usd": round(statistics.mean(costs), 8) if costs else None,
        "quality_pass_rate": (len(quality_passes) / len(quality_rows)) if quality_rows else None,
        "model_match_rate": (len(model_matches) / len(model_rows)) if model_rows else None,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Template A/B benchmark for vLLM-compatible endpoints.")
    ap.add_argument("--dataset-jsonl", default="reports/constitution/btrack_pilot/vllm_ab_dataset_sample.jsonl")
    ap.add_argument("--generate-sample-dataset", action="store_true")
    ap.add_argument("--baseline-url", required=False, help="Base URL (OpenAI-compatible) for baseline lane")
    ap.add_argument("--candidate-url", required=False, help="Base URL (OpenAI-compatible) for candidate lane")
    ap.add_argument("--baseline-model", default="baseline-model")
    ap.add_argument("--candidate-model", default="candidate-model")
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--max-tokens", type=int, default=256)
    ap.add_argument("--usd-per-1k-tokens", type=float, default=0.0, help="Estimated blended token price")
    ap.add_argument("--out-json", default="reports/constitution/btrack_pilot/vllm_ab_benchmark_latest.json")
    ap.add_argument("--latency-max-delta-pct", type=float, default=15.0, help="Candidate p95 must not exceed baseline by this pct")
    ap.add_argument("--quality-min-delta", type=float, default=0.0, help="Candidate quality_pass_rate - baseline quality_pass_rate minimum")
    args = ap.parse_args()

    dataset_path = Path(args.dataset_jsonl).resolve()
    if args.generate_sample_dataset:
        _write_sample_dataset(dataset_path)
        print(f"WROTE sample dataset: {dataset_path}")
        return 0

    if not args.baseline_url or not args.candidate_url:
        raise SystemExit("baseline-url and candidate-url are required unless --generate-sample-dataset is used")

    rows = _read_jsonl(dataset_path)
    all_eval: list[EvalRow] = []

    lanes = [
        ("baseline", args.baseline_url, args.baseline_model),
        ("candidate", args.candidate_url, args.candidate_model),
    ]

    for lane_name, lane_url, lane_model in lanes:
        for row in rows:
            cid = str(row.get("id") or f"{lane_name}_{len(all_eval)}")
            msgs = row.get("messages") or []
            expected = row.get("expected_substrings") or []
            try:
                payload, latency_ms = _post_chat(
                    url=lane_url,
                    model=lane_model,
                    messages=msgs,
                    temperature=args.temperature,
                    max_tokens=args.max_tokens,
                )
                usage = payload.get("usage") or {}
                total_tokens = usage.get("total_tokens")
                output_text = _extract_text(payload)
                quality_pass = _contains_all(output_text, expected) if expected else None
                response_model = payload.get("model")
                model_match = (response_model == lane_model) if response_model is not None else None
                all_eval.append(
                    EvalRow(
                        case_id=cid,
                        lane=lane_name,
                        ok=True,
                        latency_ms=latency_ms,
                        prompt_tokens=usage.get("prompt_tokens"),
                        completion_tokens=usage.get("completion_tokens"),
                        total_tokens=total_tokens,
                        cost_estimate_usd=_calc_cost(total_tokens, args.usd_per_1k_tokens),
                        output_text=output_text,
                        response_model=response_model,
                        expected_model=lane_model,
                        model_match=model_match,
                        quality_pass=quality_pass,
                        error=None,
                    )
                )
            except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
                all_eval.append(
                    EvalRow(
                        case_id=cid,
                        lane=lane_name,
                        ok=False,
                        latency_ms=0.0,
                        prompt_tokens=None,
                        completion_tokens=None,
                        total_tokens=None,
                        cost_estimate_usd=None,
                        output_text="",
                        response_model=None,
                        expected_model=lane_model,
                        model_match=None,
                        quality_pass=None,
                        error=str(e),
                    )
                )

    baseline_rows = [r for r in all_eval if r.lane == "baseline"]
    candidate_rows = [r for r in all_eval if r.lane == "candidate"]
    b = _lane_stats(baseline_rows)
    c = _lane_stats(candidate_rows)

    p95_delta_pct = None
    if b["p95_latency_ms"] and c["p95_latency_ms"]:
        p95_delta_pct = ((c["p95_latency_ms"] - b["p95_latency_ms"]) / b["p95_latency_ms"]) * 100.0

    quality_delta = None
    if b["quality_pass_rate"] is not None and c["quality_pass_rate"] is not None:
        quality_delta = c["quality_pass_rate"] - b["quality_pass_rate"]

    go = True
    if p95_delta_pct is not None and p95_delta_pct > args.latency_max_delta_pct:
        go = False
    if quality_delta is not None and quality_delta < args.quality_min_delta:
        go = False
    if c["model_match_rate"] is not None and c["model_match_rate"] < 1.0:
        go = False
    if c["error_count"] > 0:
        go = False

    out = Path(args.out_json).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "vllm_ab_benchmark_v1",
        "dataset": str(dataset_path),
        "thresholds": {
            "latency_max_delta_pct": args.latency_max_delta_pct,
            "quality_min_delta": args.quality_min_delta,
        },
        "baseline": b,
        "candidate": c,
        "comparative": {
            "p95_latency_delta_pct": p95_delta_pct,
            "quality_delta": quality_delta,
        },
        "go_no_go": "GO" if go else "NO_GO",
        "rows": [r.__dict__ for r in all_eval],
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"WROTE: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
