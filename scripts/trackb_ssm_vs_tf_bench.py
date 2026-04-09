#!/usr/bin/env python3
"""Track B research-only benchmark plan: SSM/Mamba vs Transformer (skeleton).

This script does not claim to run full Mamba training. It writes a reproducible
benchmark contract JSON so hardware-backed runs can slot in later.

Optional --run-smoke runs a toy CPU/GPU microbench (attention-like matmul chain
vs per-step linear recurrence). This is NOT a faithful Transformer vs Mamba
model comparison; see fact_safe_note in the micro artifact.
"""
from __future__ import annotations

import argparse
import json
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_OUT = ART / "trackb_ssm_vs_tf_bench_plan_latest.json"
DEFAULT_MICRO_OUT = ART / "trackb_ssm_vs_tf_bench_micro_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_toy_micro(
    *,
    batch: int,
    heads: int,
    seq_len: int,
    head_dim: int,
    repeats: int,
    device_str: str,
) -> dict[str, Any]:
    import torch

    if device_str == "cuda":
        if not torch.cuda.is_available():
            return {
                "status": "skipped_cuda_unavailable",
                "device_requested": device_str,
                "device_used": "cpu",
            }
        device = torch.device("cuda")
    else:
        device = torch.device("cpu")

    dtype = torch.float32
    scale = (head_dim**-0.5)

    q = torch.randn(batch, heads, seq_len, head_dim, device=device, dtype=dtype)
    k = torch.randn(batch, heads, seq_len, head_dim, device=device, dtype=dtype)
    v = torch.randn(batch, heads, seq_len, head_dim, device=device, dtype=dtype)
    w_state = torch.randn(head_dim, head_dim, device=device, dtype=dtype)
    x_steps = torch.randn(batch, seq_len, head_dim, device=device, dtype=dtype)

    def attention_like() -> None:
        scores = (q @ k.transpose(-2, -1)) * scale
        attn = torch.softmax(scores, dim=-1)
        _ = attn @ v

    def recurrence_like() -> None:
        h = torch.zeros(batch, head_dim, device=device, dtype=dtype)
        for t in range(seq_len):
            h = torch.tanh(h @ w_state + x_steps[:, t, :])

    def bench(fn: Any, warmup: int = 3, iters: int = 10) -> list[float]:
        for _ in range(warmup):
            fn()
        if device.type == "cuda":
            torch.cuda.synchronize()
        times_ms: list[float] = []
        for _ in range(iters):
            t0 = time.perf_counter()
            fn()
            if device.type == "cuda":
                torch.cuda.synchronize()
            times_ms.append((time.perf_counter() - t0) * 1000.0)
        return times_ms

    attn_times: list[float] = []
    rec_times: list[float] = []
    for _ in range(max(1, repeats)):
        attn_times.extend(bench(attention_like))
        rec_times.extend(bench(recurrence_like))

    def summarize(xs: list[float]) -> dict[str, float]:
        return {
            "ms_mean": round(statistics.mean(xs), 6),
            "ms_p50": round(statistics.median(xs), 6),
            "ms_min": round(min(xs), 6),
            "ms_max": round(max(xs), 6),
        }

    return {
        "status": "ok",
        "device_used": str(device),
        "shapes": {
            "batch": batch,
            "heads": heads,
            "seq_len": seq_len,
            "head_dim": head_dim,
        },
        "attention_like_chain": summarize(attn_times),
        "recurrence_like_scan": summarize(rec_times),
        "ratio_attention_over_recurrence": round(
            statistics.mean(attn_times) / max(1e-9, statistics.mean(rec_times)),
            6,
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="SSM vs Transformer bench plan (skeleton)")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument(
        "--micro-out",
        default=str(DEFAULT_MICRO_OUT),
        help="Output path for --run-smoke toy microbench JSON.",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Write plan only; do not invoke torch/mamba (default when neither --run-smoke).",
    )
    ap.add_argument(
        "--run-smoke",
        action="store_true",
        help="Run toy microbench (torch); not a real Mamba vs Transformer model run.",
    )
    ap.add_argument("--batch", type=int, default=1)
    ap.add_argument("--heads", type=int, default=4)
    ap.add_argument("--seq-len", type=int, default=512)
    ap.add_argument("--head-dim", type=int, default=64)
    ap.add_argument("--repeats", type=int, default=2)
    ap.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    args = ap.parse_args()

    plan = {
        "schema": "trackb_ssm_vs_tf_bench_plan_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "not_billing_claim": True,
        "objective": (
            "Under matched compute budget, compare latency peak memory on long sequences "
            "for a Transformer baseline vs an SSM/Mamba-class model (hardware run TBD)."
        ),
        "controlled_factors": [
            "identical batch size where possible",
            "identical sequence lengths sweep (e.g. 512, 2048, 8192)",
            "identical tokenizer and input distribution",
            "same hardware driver / CUDA / dtype",
        ],
        "primary_metrics": [
            "wall_latency_ms_p50_p99",
            "peak_reserved_vram_bytes",
            "throughput_tokens_per_sec",
            "task_utility_proxy (domain-specific, separate artifact)",
        ],
        "implementation_status": "skeleton_only",
        "dry_run": bool(args.dry_run or not args.run_smoke),
        "next_hardware_steps": [
            "Pin torch + mamba-ssm (or vendor fork) versions in a dedicated venv.",
            "Add minimal forward-only microbench for two frozen checkpoints.",
            "Log `nvidia-smi` peak and autograd profiler summary to reports/.",
        ],
        "fact_safe_note": (
            "O(N) vs O(N^2) claims are architecture-level; measured wins are "
            "dataset/hardware specific."
        ),
        "out_of_scope": "No production promotion, no trading trigger.",
    }

    if args.run_smoke and not args.dry_run:
        micro: dict[str, Any] = {
            "schema": "trackb_ssm_vs_tf_bench_micro_v1",
            "generated_at_utc": _utc_now(),
            "research_only": True,
            "not_billing_claim": True,
            "fact_safe_note": (
                "Toy benchmark only: softmax(QK^T)V-style chain vs explicit per-step recurrence. "
                "Does not load Mamba, Llama, or production checkpoints."
            ),
        }
        try:
            micro["result"] = _run_toy_micro(
                batch=args.batch,
                heads=args.heads,
                seq_len=args.seq_len,
                head_dim=args.head_dim,
                repeats=args.repeats,
                device_str=args.device,
            )
            if micro["result"].get("status") == "ok":
                plan["implementation_status"] = "micro_toy_ran"
        except Exception as e:  # noqa: BLE001
            micro["result"] = {"status": "error", "error": str(e)}
        plan["dry_run"] = False
        plan["last_micro_run_utc"] = micro["generated_at_utc"]

        micro_path = Path(args.micro_out) if Path(args.micro_out).is_absolute() else (ROOT / args.micro_out)
        micro_path.parent.mkdir(parents=True, exist_ok=True)
        micro_path.write_text(json.dumps(micro, ensure_ascii=False, indent=2), encoding="utf-8")
        print(str(micro_path))

    out_path = Path(args.out) if Path(args.out).is_absolute() else (ROOT / args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
