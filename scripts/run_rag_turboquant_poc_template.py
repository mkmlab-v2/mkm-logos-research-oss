#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import statistics
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CommandResult:
    elapsed_sec: float
    exit_code: int
    stdout: str
    stderr: str


def _run_once(command: str, cwd: Path) -> CommandResult:
    start = time.perf_counter()
    proc = subprocess.run(
        command,
        cwd=str(cwd),
        shell=True,
        capture_output=True,
        text=True,
    )
    elapsed = time.perf_counter() - start
    return CommandResult(
        elapsed_sec=elapsed,
        exit_code=proc.returncode,
        stdout=proc.stdout[-2000:],
        stderr=proc.stderr[-2000:],
    )


def _summary(times: list[float]) -> dict[str, float]:
    return {
        "mean_sec": round(statistics.mean(times), 4),
        "median_sec": round(statistics.median(times), 4),
        "p95_sec": round(sorted(times)[max(0, int(len(times) * 0.95) - 1)], 4),
        "min_sec": round(min(times), 4),
        "max_sec": round(max(times), 4),
    }


def _is_synthetic_command(command: str) -> bool:
    patterns = [
        r"time\.sleep\(",
        r"\bping\b",
        r"\becho\b",
    ]
    return any(re.search(p, command, flags=re.IGNORECASE) for p in patterns)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "RAG TurboQuant PoC benchmark template. "
            "Runs baseline and turbo commands repeatedly and stores timing report."
        )
    )
    parser.add_argument("--name", default="rag_turboquant_poc", help="Benchmark run name")
    parser.add_argument("--cwd", default=".", help="Working directory to run commands")
    parser.add_argument("--runs", type=int, default=5, help="Repetitions per command")
    parser.add_argument("--baseline-build-cmd", required=True, help="Baseline index build command")
    parser.add_argument("--baseline-query-cmd", required=True, help="Baseline query command")
    parser.add_argument("--turbo-build-cmd", required=True, help="TurboQuant index build command")
    parser.add_argument("--turbo-query-cmd", required=True, help="TurboQuant query command")
    parser.add_argument(
        "--output",
        default="reports/constitution/btrack_pilot/rag_turboquant_poc_latest.json",
        help="Output report path",
    )
    parser.add_argument(
        "--require-non-synthetic",
        action="store_true",
        help="Fail if any benchmark command looks synthetic.",
    )
    args = parser.parse_args()

    cwd = Path(args.cwd).resolve()
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    lanes = {
        "baseline": {
            "build_cmd": args.baseline_build_cmd,
            "query_cmd": args.baseline_query_cmd,
        },
        "turboquant": {
            "build_cmd": args.turbo_build_cmd,
            "query_cmd": args.turbo_query_cmd,
        },
    }

    report: dict[str, object] = {
        "name": args.name,
        "runs_per_stage": args.runs,
        "cwd": str(cwd),
        "lanes": {},
        "policy_note": "Apply quantization only to RAG/LLM lanes. Keep backend fact engine deterministic.",
    }
    all_commands = [
        args.baseline_build_cmd,
        args.baseline_query_cmd,
        args.turbo_build_cmd,
        args.turbo_query_cmd,
    ]
    synthetic = any(_is_synthetic_command(cmd) for cmd in all_commands)
    report["evidence_tier"] = "synthetic_smoke" if synthetic else "candidate_real_benchmark"
    report["synthetic_command_detected"] = synthetic

    failed = False
    for lane_name, lane in lanes.items():
        lane_report: dict[str, object] = {"commands": lane, "build": [], "query": []}
        build_times: list[float] = []
        query_times: list[float] = []
        for _ in range(args.runs):
            r = _run_once(lane["build_cmd"], cwd)
            lane_report["build"].append(r.__dict__)
            build_times.append(r.elapsed_sec)
            if r.exit_code != 0:
                failed = True
        for _ in range(args.runs):
            r = _run_once(lane["query_cmd"], cwd)
            lane_report["query"].append(r.__dict__)
            query_times.append(r.elapsed_sec)
            if r.exit_code != 0:
                failed = True
        lane_report["build_summary"] = _summary(build_times)
        lane_report["query_summary"] = _summary(query_times)
        report["lanes"][lane_name] = lane_report

    try:
        bq = report["lanes"]["baseline"]["query_summary"]["mean_sec"]  # type: ignore[index]
        tq = report["lanes"]["turboquant"]["query_summary"]["mean_sec"]  # type: ignore[index]
        bb = report["lanes"]["baseline"]["build_summary"]["mean_sec"]  # type: ignore[index]
        tb = report["lanes"]["turboquant"]["build_summary"]["mean_sec"]  # type: ignore[index]
        report["improvement"] = {
            "query_speedup_x": round(float(bq) / float(tq), 4) if tq else None,
            "build_speedup_x": round(float(bb) / float(tb), 4) if tb else None,
        }
    except Exception:
        report["improvement"] = {}

    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved PoC report: {output}")
    if args.require_non_synthetic and synthetic:
        print("Synthetic benchmark commands detected while --require-non-synthetic is set.")
        return 1
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
