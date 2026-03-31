#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _run(cmd: str, cwd: Path) -> tuple[float, int, str, str]:
    t0 = time.perf_counter()
    p = subprocess.run(cmd, cwd=str(cwd), shell=True, capture_output=True, text=True)
    dt = time.perf_counter() - t0
    return dt, p.returncode, p.stdout[-1500:], p.stderr[-1500:]


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _p95(values: list[float]) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    idx = max(0, int(len(s) * 0.95) - 1)
    return float(s[idx])


def main() -> int:
    ap = argparse.ArgumentParser(description="Canary monitor for guarded TurboQuant candidate (A/high).")
    ap.add_argument("--cwd", default=".", help="Working directory")
    ap.add_argument("--iterations", type=int, default=24, help="Monitoring iterations")
    ap.add_argument("--interval-sec", type=float, default=3600.0, help="Sleep seconds between iterations")
    ap.add_argument("--traffic-percent", type=int, default=10, help="Canary traffic percentage")
    ap.add_argument("--jaccard-drop-max-pp", type=float, default=1.5, help="Guardrail: max jaccard drop")
    ap.add_argument("--failure-rate-delta-max-pp", type=float, default=0.3, help="Guardrail: max failure-rate delta")
    ap.add_argument("--p95-latency-delta-max-pct", type=float, default=15.0, help="Guardrail: max p95 latency delta")
    ap.add_argument(
        "--sensitive-terms",
        default="사상의학,체질,sasang,myeongri,bible,manual,direct,evidence,strict",
        help="Comma-separated domain-sensitive terms",
    )
    ap.add_argument(
        "--out-json",
        default="reports/constitution/btrack_pilot/rag_canary_monitor_latest.json",
        help="Latest monitor snapshot JSON",
    )
    ap.add_argument(
        "--out-log",
        default="reports/constitution/btrack_pilot/rag_canary_monitor_log.jsonl",
        help="Append-only monitor log JSONL",
    )
    args = ap.parse_args()

    cwd = Path(args.cwd).resolve()
    out_json = Path(args.out_json).resolve()
    out_log = Path(args.out_log).resolve()
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_log.parent.mkdir(parents=True, exist_ok=True)

    baseline_out = "reports/constitution/btrack_pilot/rag_canary_baseline_latest.json"
    canary_out = "reports/constitution/btrack_pilot/rag_canary_candidate_latest.json"
    baseline_cmd = (
        "python scripts/report_multilens_performance_eval.py "
        f"--mode baseline --output {baseline_out}"
    )
    canary_cmd = (
        "python scripts/report_multilens_performance_eval.py "
        "--mode experimental --strategy A --intensity high "
        f"--domain-sensitive-terms \"{args.sensitive_terms}\" "
        f"--output {canary_out}"
    )

    rows: list[dict[str, Any]] = []
    start_ts = datetime.now(timezone.utc).isoformat()

    for i in range(args.iterations):
        b_t, b_code, _, b_err = _run(baseline_cmd, cwd)
        c_t, c_code, _, c_err = _run(canary_cmd, cwd)
        b_fail = 1 if b_code != 0 else 0
        c_fail = 1 if c_code != 0 else 0

        row: dict[str, Any] = {
            "iter": i + 1,
            "ts_utc": datetime.now(timezone.utc).isoformat(),
            "baseline_sec": round(b_t, 4),
            "candidate_sec": round(c_t, 4),
            "baseline_failed": b_fail,
            "candidate_failed": c_fail,
        }

        if c_code == 0 and (cwd / canary_out).exists():
            rep = _read_json((cwd / canary_out).resolve())
            qg = rep.get("quality_gate", {})
            row["jaccard_drop_pp"] = float(qg.get("jaccard_drop_pp", 0.0) or 0.0)
            row["jaccard_guardrail_ok"] = bool(qg.get("jaccard_guardrail_ok", False))
            row["sensitive_integrity_ok"] = bool(qg.get("sensitive_integrity_ok", False))
        else:
            row["jaccard_drop_pp"] = None
            row["jaccard_guardrail_ok"] = False
            row["sensitive_integrity_ok"] = False
            if c_err:
                row["candidate_error"] = c_err
        if b_code != 0 and b_err:
            row["baseline_error"] = b_err

        rows.append(row)
        out_log.write_text(
            (out_log.read_text(encoding="utf-8") if out_log.exists() else "")
            + json.dumps(row, ensure_ascii=False)
            + "\n",
            encoding="utf-8",
        )
        if i < args.iterations - 1 and args.interval_sec > 0:
            time.sleep(args.interval_sec)

    baseline_lat = [float(r["baseline_sec"]) for r in rows]
    candidate_lat = [float(r["candidate_sec"]) for r in rows]
    baseline_fail_rate = 100.0 * sum(int(r["baseline_failed"]) for r in rows) / len(rows)
    candidate_fail_rate = 100.0 * sum(int(r["candidate_failed"]) for r in rows) / len(rows)
    failure_rate_delta_pp = candidate_fail_rate - baseline_fail_rate
    p95_base = _p95(baseline_lat)
    p95_cand = _p95(candidate_lat)
    p95_latency_delta_pct = ((p95_cand - p95_base) / p95_base * 100.0) if p95_base > 0 else 0.0
    jaccard_vals = [float(r["jaccard_drop_pp"]) for r in rows if r.get("jaccard_drop_pp") is not None]
    jaccard_drop_pp_max_observed = max(jaccard_vals) if jaccard_vals else None

    guardrail_status = {
        "failure_rate_delta_ok": failure_rate_delta_pp <= args.failure_rate_delta_max_pp,
        "p95_latency_delta_ok": p95_latency_delta_pct <= args.p95_latency_delta_max_pct,
        "jaccard_drop_ok": (
            jaccard_drop_pp_max_observed is not None and jaccard_drop_pp_max_observed <= args.jaccard_drop_max_pp
        ),
        "all_passed": False,
    }
    guardrail_status["all_passed"] = bool(
        guardrail_status["failure_rate_delta_ok"]
        and guardrail_status["p95_latency_delta_ok"]
        and guardrail_status["jaccard_drop_ok"]
    )

    report = {
        "schema": "rag_turboquant_canary_monitor_v1",
        "started_at_utc": start_ts,
        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        "candidate": {"strategy": "A", "intensity": "high"},
        "traffic_percent": args.traffic_percent,
        "iterations": args.iterations,
        "summary": {
            "baseline_mean_sec": round(statistics.mean(baseline_lat), 4),
            "candidate_mean_sec": round(statistics.mean(candidate_lat), 4),
            "baseline_p95_sec": round(p95_base, 4),
            "candidate_p95_sec": round(p95_cand, 4),
            "p95_latency_delta_pct": round(p95_latency_delta_pct, 4),
            "baseline_failure_rate_pct": round(baseline_fail_rate, 4),
            "candidate_failure_rate_pct": round(candidate_fail_rate, 4),
            "failure_rate_delta_pp": round(failure_rate_delta_pp, 4),
            "jaccard_drop_pp_max_observed": round(jaccard_drop_pp_max_observed, 4)
            if jaccard_drop_pp_max_observed is not None
            else None,
        },
        "thresholds": {
            "jaccard_drop_max_pp": args.jaccard_drop_max_pp,
            "failure_rate_delta_max_pp": args.failure_rate_delta_max_pp,
            "p95_latency_delta_max_pct": args.p95_latency_delta_max_pct,
        },
        "guardrail_status": guardrail_status,
        "last_rows": rows[-min(10, len(rows)) :],
    }
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved canary monitor report: {out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
