#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import time
from pathlib import Path
from typing import Any


def _run(cmd: str, cwd: Path) -> tuple[float, int, str, str]:
    t0 = time.perf_counter()
    p = subprocess.run(cmd, cwd=str(cwd), shell=True, capture_output=True, text=True)
    dt = time.perf_counter() - t0
    return dt, p.returncode, p.stdout[-1500:], p.stderr[-1500:]


def _mean(xs: list[float]) -> float:
    return float(statistics.mean(xs)) if xs else 0.0


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Sweep experimental compression profiles and select fastest guardrail-passing candidate."
    )
    ap.add_argument("--cwd", default=".", help="Working directory")
    ap.add_argument("--runs", type=int, default=3, help="Repetitions per command")
    ap.add_argument(
        "--sensitive-terms",
        default="사상의학,체질,sasang,myeongri,bible,manual,direct,evidence,strict",
        help="Comma-separated domain-sensitive terms",
    )
    ap.add_argument(
        "--output",
        default="reports/constitution/btrack_pilot/rag_turboquant_guarded_sweep_latest.json",
        help="Output JSON path",
    )
    args = ap.parse_args()

    cwd = Path(args.cwd).resolve()
    out = Path(args.output).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    strategies = ["A", "B", "C"]
    intensities = ["high", "ultra", "extreme"]

    baseline_build_cmd = (
        "python scripts/report_multilens_performance_eval.py "
        "--mode baseline "
        "--output reports/constitution/btrack_pilot/rag_guard_baseline_build_latest.json"
    )
    baseline_query_cmd = (
        "python scripts/report_multilens_performance_eval.py "
        "--mode baseline "
        "--output reports/constitution/btrack_pilot/rag_guard_baseline_query_latest.json"
    )

    baseline_build_times: list[float] = []
    baseline_query_times: list[float] = []
    for _ in range(args.runs):
        t, code, _, err = _run(baseline_build_cmd, cwd)
        if code != 0:
            raise RuntimeError(f"Baseline build failed: {err}")
        baseline_build_times.append(t)
    for _ in range(args.runs):
        t, code, _, err = _run(baseline_query_cmd, cwd)
        if code != 0:
            raise RuntimeError(f"Baseline query failed: {err}")
        baseline_query_times.append(t)

    baseline_build_mean = _mean(baseline_build_times)
    baseline_query_mean = _mean(baseline_query_times)

    candidates: list[dict[str, Any]] = []
    for s in strategies:
        for i in intensities:
            out_build = f"reports/constitution/btrack_pilot/rag_guard_{s}_{i}_build_latest.json"
            out_query = f"reports/constitution/btrack_pilot/rag_guard_{s}_{i}_query_latest.json"
            build_cmd = (
                "python scripts/report_multilens_performance_eval.py "
                f"--mode experimental --strategy {s} --intensity {i} "
                f"--domain-sensitive-terms \"{args.sensitive_terms}\" "
                f"--output {out_build}"
            )
            query_cmd = (
                "python scripts/report_multilens_performance_eval.py "
                f"--mode experimental --strategy {s} --intensity {i} "
                f"--domain-sensitive-terms \"{args.sensitive_terms}\" "
                f"--output {out_query}"
            )
            build_times: list[float] = []
            query_times: list[float] = []
            for _ in range(args.runs):
                t, code, _, err = _run(build_cmd, cwd)
                if code != 0:
                    raise RuntimeError(f"Experimental build failed ({s}/{i}): {err}")
                build_times.append(t)
            for _ in range(args.runs):
                t, code, _, err = _run(query_cmd, cwd)
                if code != 0:
                    raise RuntimeError(f"Experimental query failed ({s}/{i}): {err}")
                query_times.append(t)

            rep = _load_json((cwd / out_query).resolve())
            qg = rep.get("quality_gate", {})
            cm = rep.get("compression_metrics", {})
            build_mean = _mean(build_times)
            query_mean = _mean(query_times)
            candidates.append(
                {
                    "strategy": s,
                    "intensity": i,
                    "build_mean_sec": round(build_mean, 4),
                    "query_mean_sec": round(query_mean, 4),
                    "build_speedup_x": round(baseline_build_mean / build_mean, 4) if build_mean else None,
                    "query_speedup_x": round(baseline_query_mean / query_mean, 4) if query_mean else None,
                    "global_token_saving_rate": cm.get("global_token_saving_rate"),
                    "avg_reconstruction_fidelity_jaccard": cm.get("avg_reconstruction_fidelity_jaccard"),
                    "avg_sensitive_integrity": cm.get("avg_sensitive_integrity"),
                    "ultra_saving_50_ok": qg.get("ultra_saving_50_ok"),
                    "jaccard_guardrail_ok": qg.get("jaccard_guardrail_ok"),
                    "sensitive_integrity_ok": qg.get("sensitive_integrity_ok"),
                    "gate_pass": bool(qg.get("jaccard_guardrail_ok") and qg.get("sensitive_integrity_ok")),
                    "query_report_path": out_query,
                }
            )

    passing = [c for c in candidates if c["gate_pass"]]
    best = None
    if passing:
        best = sorted(
            passing,
            key=lambda c: (
                float(c["query_speedup_x"] or 0.0),
                float(c["build_speedup_x"] or 0.0),
            ),
            reverse=True,
        )[0]

    result = {
        "schema": "rag_turboquant_guarded_sweep_v1",
        "runs": args.runs,
        "baseline": {
            "build_mean_sec": round(baseline_build_mean, 4),
            "query_mean_sec": round(baseline_query_mean, 4),
        },
        "sensitive_terms": args.sensitive_terms,
        "candidate_count": len(candidates),
        "candidates": candidates,
        "passing_count": len(passing),
        "best_guarded_candidate": best,
        "recommendation": (
            "NO_GO: no candidate satisfied jaccard+sensitive guardrails"
            if best is None
            else f"GO_CANDIDATE: {best['strategy']}/{best['intensity']}"
        ),
    }

    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved guarded sweep report: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
