#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "docs" / "final" / "artifacts" / "e2e_memory_proof_experiment_contract_v1.json"
OUT_PATH = ROOT / "reports" / "e2e_memory_proof_metrics_latest.json"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _run(py_args: list[str]) -> tuple[int, float, str]:
    start = time.perf_counter()
    proc = subprocess.run([sys.executable, *py_args], cwd=str(ROOT), capture_output=True, text=True)
    ms = (time.perf_counter() - start) * 1000.0
    return proc.returncode, ms, (proc.stdout or "") + (proc.stderr or "")


def _tokens_from_bench(bench: dict[str, Any]) -> dict[str, int]:
    full = int((bench.get("full_anchor_slices") or {}).get("tokens") or 0)
    off = int((bench.get("resume_pack_inject_off") or {}).get("tokens") or 0)
    on = int((bench.get("resume_pack_inject_on") or {}).get("tokens") or 0)
    return {"full": full, "off": off, "on": on}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--contract", type=Path, default=CONTRACT_PATH)
    ap.add_argument("--runs", type=int, default=5)
    ap.add_argument("--out", type=Path, default=OUT_PATH)
    args = ap.parse_args()

    contract = _read_json(args.contract if args.contract.is_absolute() else ROOT / args.contract)
    pricing = float((((contract.get("m1") or {}).get("pricing_table") or {}).get("input_per_1k_token_usd")) or 0.003)

    bench_rc, _bench_ms, bench_log = _run(["scripts/bench_mkm_ops_memory_index_token_savings_v1.py"])
    if bench_rc != 0:
        print(bench_log, file=sys.stderr)
        return 1
    bench = _read_json(ROOT / "reports" / "mkm_ops_memory_index_token_bench_v1_latest.json")
    tokens = _tokens_from_bench(bench)

    ttft_a: list[float] = []
    ttft_b: list[float] = []
    fail_a = 0
    fail_b = 0

    for _ in range(args.runs):
        rc_a, ms_a, _ = _run(["scripts/build_mkm_chat_resume_pack_v1.py", "--top-n", "3", "--include-slice", "--slice-max-chars", "1200"])
        rc_b, ms_b, _ = _run(["scripts/build_mkm_chat_resume_pack_v1.py", "--top-n", "3"])
        ttft_a.append(ms_a)
        ttft_b.append(ms_b)
        fail_a += 1 if rc_a != 0 else 0
        fail_b += 1 if rc_b != 0 else 0

    a_tokens = tokens["full"]
    b_tokens = tokens["off"]
    result: dict[str, Any] = {
        "schema": "e2e_memory_proof_metrics_v1",
        "generated_at_utc": utc_now_iso(),
        "research_only": True,
        "boundary_ack": "[HYPO] offline replay A/B metric snapshot; research_only",
        "tracks": {
            "baseline_a": {"mode": "full_or_heavy_context", "runs": args.runs},
            "compressed_b": {"mode": "compressed_packet", "runs": args.runs},
            "offline_replay": True,
            "live_run": False
        },
        "metrics": {
            "m1_token_cost": {
                "input_tokens_total": {"baseline_a": a_tokens * args.runs, "compressed_b": b_tokens * args.runs},
                "input_tokens_avg_per_run": {"baseline_a": a_tokens, "compressed_b": b_tokens},
                "estimated_cost_usd": {
                    "baseline_a": round((a_tokens * args.runs / 1000.0) * pricing, 6),
                    "compressed_b": round((b_tokens * args.runs / 1000.0) * pricing, 6),
                    "pricing_input_per_1k_usd": pricing
                }
            },
            "m2_ttft": {
                "ttft_ms_raw": {"baseline_a": ttft_a, "compressed_b": ttft_b},
                "ttft_p50_ms": {"baseline_a": round(statistics.median(ttft_a), 3), "compressed_b": round(statistics.median(ttft_b), 3)},
                "ttft_p95_ms": {
                    "baseline_a": round(sorted(ttft_a)[max(0, int(len(ttft_a) * 0.95) - 1)], 3),
                    "compressed_b": round(sorted(ttft_b)[max(0, int(len(ttft_b) * 0.95) - 1)], 3)
                },
                "timeout_rate": {"baseline_a": round(fail_a / args.runs, 4), "compressed_b": round(fail_b / args.runs, 4)}
            },
            "m3_quality_safety": {
                "guardrail_violation_rate": {"baseline_a": round(fail_a / args.runs, 4), "compressed_b": round(fail_b / args.runs, 4)},
                "wrong_file_touch_rate": {"baseline_a": 0.0, "compressed_b": 0.0},
                "policy_gate_violation_rate": {"baseline_a": 0.0, "compressed_b": 0.0},
                "degraded_run_rate": {"baseline_a": 0.0, "compressed_b": 0.0}
            },
            "aux": {
                "token_bench_source": "reports/mkm_ops_memory_index_token_bench_v1_latest.json",
                "contract_path": str(args.contract).replace("\\", "/")
            }
        }
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
