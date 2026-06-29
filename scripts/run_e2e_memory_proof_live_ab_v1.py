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
OUT_PATH = ROOT / "reports" / "e2e_memory_proof_live_metrics_latest.json"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _run_cmd(cmd: list[str]) -> tuple[int, float, str]:
    start = time.perf_counter()
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    ms = (time.perf_counter() - start) * 1000.0
    return proc.returncode, ms, (proc.stdout or "") + (proc.stderr or "")


def _run_live_arm(
    include_slice: bool,
    execute_guard: bool,
    *,
    runs: int,
    guard_samples: int,
) -> dict[str, Any]:
    ttft_list: list[float] = []
    build_errors = 0
    guard_errors = 0
    degraded_hits = 0

    for _ in range(runs):
        args = ["scripts/build_mkm_chat_resume_pack_v1.py", "--top-n", "3"]
        if include_slice:
            args.extend(["--include-slice", "--slice-max-chars", "1200"])
        rc, ms, _ = _run_cmd([sys.executable, *args])
        ttft_list.append(ms)
        if rc != 0:
            build_errors += 1

    if execute_guard:
        guard_doc = {}
        for _ in range(guard_samples):
            rc_guard, _guard_ms, _ = _run_cmd(
                [
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(
                        ROOT
                        / "projects"
                        / "bitcoin-trading"
                        / "ops"
                        / "windows-rehearsal"
                        / "run_daily_minimum_ops_guard.ps1"
                    ),
                    "-SkipHeadlineIntegrityCheck",
                ]
            )
            if rc_guard != 0:
                guard_errors += 1
            guard_doc = _read_json(
                ROOT
                / "projects"
                / "bitcoin-trading"
                / "memory"
                / "v2"
                / "ops"
                / "daily_minimum_ops_guard_latest.json"
            )
            if bool(guard_doc.get("degraded_run")):
                degraded_hits += 1
    else:
        guard_doc = {}

    p50 = statistics.median(ttft_list) if ttft_list else 0.0
    p95 = sorted(ttft_list)[max(0, int(len(ttft_list) * 0.95) - 1)] if ttft_list else 0.0
    return {
        "ttft_ms_raw": ttft_list,
        "ttft_p50_ms": round(p50, 3),
        "ttft_p95_ms": round(p95, 3),
        # Composite keeps backward compatibility, but track-level rates are authoritative.
        "failure_rate": round(
            (
                (build_errors / max(1, len(ttft_list)))
                + (guard_errors / max(1, guard_samples) if execute_guard else 0.0)
            )
            / (2.0 if execute_guard else 1.0),
            4,
        ),
        "build_failure_rate": round(build_errors / max(1, len(ttft_list)), 4),
        "guard_failure_rate": round(guard_errors / max(1, guard_samples), 4) if execute_guard else 0.0,
        "degraded_run_rate": round(degraded_hits / max(1, guard_samples), 4) if execute_guard else 0.0,
        "runs": runs,
        "guard_samples": guard_samples if execute_guard else 0,
        "guard_summary": {
            "status": guard_doc.get("status"),
            "degraded_run": guard_doc.get("degraded_run"),
            "degraded_reasons": guard_doc.get("degraded_reasons")
        }
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--execute-guard", action="store_true")
    ap.add_argument("--runs", type=int, default=3, help="TTFT samples per arm (use >=20 for stabilization).")
    ap.add_argument("--guard-samples", type=int, default=1, help="Guard executions per arm when --execute-guard is set.")
    ap.add_argument("--out", type=Path, default=OUT_PATH)
    args = ap.parse_args()
    runs = max(1, int(args.runs))
    guard_samples = max(1, int(args.guard_samples))

    arm_a = _run_live_arm(
        include_slice=True,
        execute_guard=args.execute_guard,
        runs=runs,
        guard_samples=guard_samples,
    )
    arm_b = _run_live_arm(
        include_slice=False,
        execute_guard=args.execute_guard,
        runs=runs,
        guard_samples=guard_samples,
    )

    doc: dict[str, Any] = {
        "schema": "e2e_memory_proof_live_metrics_v1",
        "generated_at_utc": utc_now_iso(),
        "research_only": True,
        "boundary_ack": "[HYPO] controlled live A/B metrics only",
        "tracks": {
            "baseline_a": {"mode": "heavy_context"},
            "compressed_b": {"mode": "compressed_packet"},
            "live_run": True,
            "execute_guard": args.execute_guard,
            "runs_per_arm": runs,
            "guard_samples_per_arm": guard_samples if args.execute_guard else 0,
        },
        "metrics": {
            "m2_ttft": {
                "baseline_a": arm_a,
                "compressed_b": arm_b
            },
            "m3_quality_safety": {
                "guardrail_violation_rate": {
                    # Guardrail violation is modeled as build-path contract failure.
                    "baseline_a": arm_a["build_failure_rate"],
                    "compressed_b": arm_b["build_failure_rate"]
                },
                "guard_step_failure_rate": {
                    "baseline_a": arm_a["guard_failure_rate"],
                    "compressed_b": arm_b["guard_failure_rate"]
                },
                "composite_failure_rate": {
                    "baseline_a": arm_a["failure_rate"],
                    "compressed_b": arm_b["failure_rate"]
                },
                "degraded_run_rate": {
                    "baseline_a": arm_a["degraded_run_rate"],
                    "compressed_b": arm_b["degraded_run_rate"]
                }
            }
        }
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
