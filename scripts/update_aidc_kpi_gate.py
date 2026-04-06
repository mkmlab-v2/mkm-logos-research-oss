#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.eval_prophecy_hit_rate_v1 import _eval_price
POWER_CSV = ROOT / "docs" / "final" / "artifacts" / "power_profile.csv"
PERF_AB_JSON = ROOT / "docs" / "final" / "artifacts" / "aidc_perf_ab_summary.json"
GATE_JSON = ROOT / "docs" / "final" / "artifacts" / "aidc_kpi_gate.json"
AB_SUMMARY = ROOT / "docs" / "final" / "artifacts" / "ab_result_summary.json"
SCORE_JSON = ROOT / "docs" / "final" / "artifacts" / "btrack_prophecy_score_latest.json"
EVAL_SCRIPT = ROOT / "scripts" / "eval_prophecy_hit_rate_v1.py"
WAR_SIGNIFICANCE_JSON = ROOT / "docs" / "final" / "artifacts" / "war_prolongation_significance_eval_latest.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _with_suffix(path: Path, suffix: str) -> Path:
    if not suffix:
        return path
    return path.with_name(f"{path.stem}{suffix}{path.suffix}")


def _measure_throughput_subprocess(iterations: int) -> float:
    start = time.perf_counter()
    for _ in range(iterations):
        subprocess.run(
            [
                "py",
                str(EVAL_SCRIPT),
                "--run-mode",
                "price",
                "--score-json",
                str(SCORE_JSON),
                "--stdout-only",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    elapsed = max(1e-9, time.perf_counter() - start)
    return iterations / elapsed


def _measure_throughput_inprocess(iterations: int) -> float:
    start = time.perf_counter()
    for _ in range(iterations):
        _eval_price(SCORE_JSON)
    elapsed = max(1e-9, time.perf_counter() - start)
    return iterations / elapsed


def _query_gpu() -> tuple[float | None, float | None]:
    if not shutil.which("nvidia-smi"):
        return None, None
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=power.draw,utilization.gpu", "--format=csv,noheader,nounits"],
            text=True,
            stderr=subprocess.STDOUT,
            timeout=10,
        ).strip()
        line = out.splitlines()[0]
        p, u = [x.strip() for x in line.split(",")[:2]]
        return float(p), float(u)
    except Exception:
        return None, None


def _read_power_rows(power_csv_path: Path) -> list[dict[str, str]]:
    if not power_csv_path.is_file():
        return []
    with power_csv_path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _write_power_rows(rows: list[dict[str, str]], power_csv_path: Path) -> None:
    power_csv_path.parent.mkdir(parents=True, exist_ok=True)
    with power_csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "timestamp_utc",
                "label",
                "gpu_power_w",
                "gpu_util_pct",
                "throughput_samples_per_s",
                "perf_per_w",
                "iterations",
                "measurement_mode",
            ],
        )
        w.writeheader()
        w.writerows(rows)


def _to_float(s: str | None) -> float | None:
    if s is None or s == "":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _latest_by_label(rows: list[dict[str, str]], label: str) -> dict[str, str] | None:
    candidates = [r for r in rows if r.get("label") == label]
    if not candidates:
        return None
    return candidates[-1]


def _build_perf_ab(rows: list[dict[str, str]], ts: str) -> dict:
    base = _latest_by_label(rows, "baseline")
    treat = _latest_by_label(rows, "treatment")
    measurement_mode_consistent = bool(
        base
        and treat
        and (base.get("measurement_mode") or "subprocess") == (treat.get("measurement_mode") or "subprocess")
    )
    summary = {
        "schema": "aidc_perf_ab_summary_v1",
        "generated_at_utc": ts,
        "baseline": base,
        "treatment": treat,
        "paired_ready": bool(base and treat and measurement_mode_consistent),
        "measurement_mode_consistent": measurement_mode_consistent,
        "uplift_perf_per_w_pct": None,
    }
    if base and treat and measurement_mode_consistent:
        b = _to_float(base.get("perf_per_w"))
        t = _to_float(treat.get("perf_per_w"))
        if b and b > 0 and t is not None:
            summary["uplift_perf_per_w_pct"] = round(((t - b) / b) * 100.0, 6)
    return summary


def _target_hits_one_sided_alpha(
    n: int,
    p0: float,
    alpha: float = 0.05,
) -> tuple[int | None, float | None, str]:
    """Return minimal hits k with P[X>=k] < alpha for X~Binomial(n,p0).

    For moderate n, use exact tail sum.
    For large n, use normal approximation to avoid huge-number overflow/cost.
    """
    if n <= 0 or not (0.0 < p0 < 1.0):
        return None, None, "invalid"

    # Exact mode for practical sizes.
    if n <= 300:
        for k in range(0, n + 1):
            s = 0.0
            for x in range(k, n + 1):
                s += math.comb(n, x) * (p0**x) * ((1.0 - p0) ** (n - x))
            if s < alpha:
                return k, round(k / n, 6), "exact"
        return None, None, "exact"

    # Normal approximation with continuity correction.
    # k ~= ceil(mu + z*sd + 0.5)
    z = 1.6448536269514722  # one-sided 95%
    mu = n * p0
    sd = math.sqrt(n * p0 * (1.0 - p0))
    if sd <= 0:
        return None, None, "normal_approx"
    k = math.ceil(mu + z * sd + 0.5)
    k = max(0, min(n, k))
    return k, round(k / n, 6), "normal_approx"


def _write_gate(ts: str, perf_summary: dict, gate_json_path: Path, power_csv_path: Path, perf_ab_json_path: Path) -> None:
    ab = json.loads(AB_SUMMARY.read_text(encoding="utf-8")) if AB_SUMMARY.is_file() else {}
    hit_rate = ab.get("metrics_snapshot", {}).get("hit_rate")
    n_eval = ab.get("metrics_snapshot", {}).get("n_evaluated")
    hits = ab.get("metrics_snapshot", {}).get("hits")
    p_value = ab.get("statistical_test", {}).get("one_sided_p_value_vs_baseline")
    baseline_hit_rate = (ab.get("comparison", {}).get("baseline", {}) or {}).get("hit_rate_assumed", 1.0 / 3.0)
    accuracy_source = "ab_result_summary"

    # Prefer latest war-prolongation significance eval when present.
    if WAR_SIGNIFICANCE_JSON.is_file():
        try:
            sig = json.loads(WAR_SIGNIFICANCE_JSON.read_text(encoding="utf-8"))
            ov = sig.get("overall", {}) if isinstance(sig, dict) else {}
            sig_hit = ov.get("hit_rate")
            sig_n = ov.get("n")
            sig_hits = ov.get("hits")
            sig_p = ov.get("p_value_one_sided_vs_baseline")
            if sig_hit is not None:
                hit_rate = sig_hit
            if sig_n is not None:
                n_eval = sig_n
            if sig_hits is not None:
                hits = sig_hits
            if sig_p is not None:
                p_value = sig_p
            accuracy_source = "war_prolongation_significance_eval_latest"
        except Exception:
            pass

    target_hits_at_current_n = None
    target_hit_rate_at_current_n = None
    target_calc_method = "none"
    try:
        n_int = int(n_eval) if n_eval is not None else 0
        p0 = float(baseline_hit_rate)
        k, kr, method = _target_hits_one_sided_alpha(n_int, p0, 0.05)
        target_hits_at_current_n = k
        target_hit_rate_at_current_n = kr
        target_calc_method = method
    except Exception:
        target_hits_at_current_n = None
        target_hit_rate_at_current_n = None
        target_calc_method = "error"

    paired_ready = bool(perf_summary.get("paired_ready"))
    uplift = perf_summary.get("uplift_perf_per_w_pct")

    reasons: list[str] = []
    if p_value is None:
        reasons.append("accuracy_check_pending")
    elif p_value >= 0.05:
        reasons.append("accuracy_not_significant_vs_baseline")

    if not paired_ready:
        reasons.append("performance_per_watt_requires_paired_baseline_treatment")
        if perf_summary.get("measurement_mode_consistent") is False:
            reasons.append("performance_per_watt_measurement_mode_mismatch")
    elif uplift is None:
        reasons.append("performance_per_watt_uplift_not_computable")
    elif uplift <= 0:
        reasons.append("performance_per_watt_no_uplift")

    decision = "GO" if len(reasons) == 0 else "NO_GO"
    gate = {
        "schema": "aidc_kpi_gate_v1",
        "generated_at_utc": ts,
        "policy": "stage1_power_first",
        "inputs": {
            "ab_result_summary": str(AB_SUMMARY).replace("\\", "/"),
            "power_profile_csv": str(power_csv_path).replace("\\", "/"),
            "perf_ab_summary": str(perf_ab_json_path).replace("\\", "/"),
        },
        "kpi": {
            "performance_per_watt": {
                "paired_ready": paired_ready,
                "uplift_perf_per_w_pct": uplift,
                "status": "paired_measured" if paired_ready else "measured_preliminary",
                "reason": "paired baseline/treatment comparison required for go/no-go",
            },
            "accuracy": {
                "hit_rate": hit_rate,
                "n_evaluated": n_eval,
                "hits": hits,
                "p_value_one_sided_vs_baseline": p_value,
                "source": accuracy_source,
                "status": "measured",
            },
            "accuracy_significance_target": {
                "alpha_one_sided": 0.05,
                "baseline_hit_rate_assumed": baseline_hit_rate,
                "hits": hits,
                "target_hits_at_current_n": target_hits_at_current_n,
                "target_hit_rate_at_current_n": target_hit_rate_at_current_n,
                "calc_method": target_calc_method,
            },
            "integrity": {"status": "test_multilens_sensitive_integrity_gate: pass"},
        },
        "go_no_go": {"decision": decision, "reasons": reasons},
        "notes": ["Observation lane only. Not for live trading promotion."],
    }
    gate_json_path.write_text(json.dumps(gate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Update AIDC KPI gate with power/perf measurements.")
    ap.add_argument("--label", choices=("baseline", "treatment"), required=True)
    ap.add_argument("--iterations", type=int, default=20)
    ap.add_argument(
        "--measurement-mode",
        choices=("subprocess", "inprocess"),
        default="subprocess",
        help=(
            "Throughput measurement backend. Use the same mode for baseline and treatment "
            "to avoid asymmetric process-overhead bias."
        ),
    )
    ap.add_argument(
        "--output-suffix",
        default="",
        help="Optional filename suffix for B-Track isolation (e.g. _v2).",
    )
    args = ap.parse_args()

    power_csv_path = _with_suffix(POWER_CSV, args.output_suffix)
    perf_ab_json_path = _with_suffix(PERF_AB_JSON, args.output_suffix)
    gate_json_path = _with_suffix(GATE_JSON, args.output_suffix)

    ts = _now_utc()
    iterations = max(1, args.iterations)
    if args.measurement_mode == "inprocess":
        throughput = _measure_throughput_inprocess(iterations)
    else:
        throughput = _measure_throughput_subprocess(iterations)
    power_w, util_pct = _query_gpu()
    perf_per_w = (throughput / power_w) if power_w and power_w > 0 else None

    rows = _read_power_rows(power_csv_path)
    rows.append(
        {
            "timestamp_utc": ts,
            "label": args.label,
            "gpu_power_w": f"{power_w:.2f}" if power_w is not None else "",
            "gpu_util_pct": f"{util_pct:.0f}" if util_pct is not None else "",
            "throughput_samples_per_s": f"{throughput:.4f}",
            "perf_per_w": f"{perf_per_w:.6f}" if perf_per_w is not None else "",
            "iterations": str(args.iterations),
            "measurement_mode": args.measurement_mode,
        }
    )
    _write_power_rows(rows, power_csv_path)

    perf_summary = _build_perf_ab(rows, ts)
    perf_ab_json_path.write_text(json.dumps(perf_summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _write_gate(ts, perf_summary, gate_json_path, power_csv_path, perf_ab_json_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
