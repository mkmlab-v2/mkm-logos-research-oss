# -*- coding: utf-8 -*-
"""B-track spike: log-window metrics vs Myeongri 4D (S,L,K,M) correlations.

Input: JSONL rows schema ``log_myeongri_correlation_input_row_v1``.
Output: single JSON ``log_myeongri_correlation_output_v0`` with guardrails.

Uses ``MyeongriCompleteFusion`` with *window_start_utc* wall components (UTC) as the
calendar moment passed into the same pillar→오행→4D path as birth-time fusion (B-track
observation only; not clinical, not deterministic, not production gating).

Hypothesis pairs (Fact-Lock, aligned with ``tools/core/myeongri_4d_correction``):
  - L vs error_rate
  - M vs diversity_ratio (earth+water condensed axis)
  - ||V||_2 vs total_requests
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_WS = Path(__file__).resolve().parent.parent
if str(_WS) not in sys.path:
    sys.path.insert(0, str(_WS))

from scripts.myeongri_complete_fusion import MyeongriCompleteFusion

MIN_VALID_WINDOWS_DEFAULT = 30
INPUT_SCHEMA = "log_myeongri_correlation_input_row_v1"
OUTPUT_SCHEMA = "log_myeongri_correlation_output_v0"


def _parse_window_start_utc(s: str) -> datetime:
    t = s.strip()
    if t.endswith("Z"):
        t = t[:-1] + "+00:00"
    dt = datetime.fromisoformat(t)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _rankdata(a: List[float]) -> List[float]:
    """Average ranks for Spearman (ties handled)."""
    indexed = sorted(enumerate(a), key=lambda x: x[1])
    ranks = [0.0] * len(a)
    i = 0
    n = len(a)
    while i < n:
        j = i
        val = indexed[i][1]
        while j < n and indexed[j][1] == val:
            j += 1
        avg_rank = (i + j + 1) / 2.0  # 1-based average
        for k in range(i, j):
            orig_idx = indexed[k][0]
            ranks[orig_idx] = avg_rank
        i = j
    return ranks


def _pearson_r(xs: List[float], ys: List[float]) -> float:
    n = len(xs)
    if n < 2:
        return float("nan")
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((xs[i] - mx) * (ys[i] - my) for i in range(n))
    denx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    deny = math.sqrt(sum((y - my) ** 2 for y in ys))
    if denx <= 0.0 or deny <= 0.0:
        return float("nan")
    return num / (denx * deny)


def _spearman_r(xs: List[float], ys: List[float]) -> float:
    return _pearson_r(_rankdata(xs), _rankdata(ys))


def _try_scipy_pvalues(
    xs: List[float], ys: List[float]
) -> Tuple[Optional[float], Optional[float], Optional[float], Optional[float]]:
    try:
        from scipy.stats import pearsonr, spearmanr

        pr = pearsonr(xs, ys)
        sr = spearmanr(xs, ys)
        pr_r = float(pr.statistic) if hasattr(pr, "statistic") else float(pr[0])
        pr_p = float(pr.pvalue) if hasattr(pr, "pvalue") else float(pr[1])
        sr_r = float(sr.statistic) if hasattr(sr, "statistic") else float(sr[0])
        sr_p = float(sr.pvalue) if hasattr(sr, "pvalue") else float(sr[1])
        return pr_r, pr_p, sr_r, sr_p
    except Exception:
        return None, None, None, None


def _l2_norm(v: Dict[str, float]) -> float:
    return math.sqrt(sum(float(v[k]) ** 2 for k in ("S", "L", "K", "M")))


def _validate_input_row(obj: Dict[str, Any], line_no: int) -> None:
    if obj.get("schema") != INPUT_SCHEMA:
        raise ValueError(f"line {line_no}: schema must be {INPUT_SCHEMA!r}")
    rm = obj.get("run_metadata") or {}
    for k in ("run_id", "source", "environment"):
        if k not in rm or not isinstance(rm[k], str) or not rm[k]:
            raise ValueError(f"line {line_no}: run_metadata.{k} required non-empty string")
    if "window_start_utc" not in obj:
        raise ValueError(f"line {line_no}: window_start_utc required")
    wm = obj.get("window_minutes")
    if not isinstance(wm, int) or wm <= 0:
        raise ValueError(f"line {line_no}: window_minutes must be positive int")
    m = obj.get("metrics") or {}
    for k in ("total_requests", "error_count", "unique_trace_ids"):
        if k not in m or not isinstance(m[k], int) or m[k] < 0:
            raise ValueError(f"line {line_no}: metrics.{k} required non-negative int")


def _correlation_block(
    xs: List[float],
    ys: List[float],
) -> Dict[str, Any]:
    pr = _pearson_r(xs, ys)
    sr = _spearman_r(xs, ys)
    p_p, p_s = None, None
    sp_pr, sp_pp, sp_sr, sp_ps = _try_scipy_pvalues(xs, ys)
    if sp_pr is not None:
        pr = sp_pr
    if sp_sr is not None:
        sr = sp_sr
    if sp_pp is not None:
        p_p = sp_pp
    if sp_ps is not None:
        p_s = sp_ps
    out: Dict[str, Any] = {
        "pearson": None if math.isnan(pr) else round(pr, 8),
        "spearman": None if math.isnan(sr) else round(sr, 8),
        "p_value_pearson": None if p_p is None else round(float(p_p), 8),
        "p_value_spearman": None if p_s is None else round(float(p_s), 8),
        "valid_windows": len(xs),
    }
    return out


def run_correlation(
    rows: List[Dict[str, Any]],
    *,
    min_valid_windows: int,
    is_solar: bool,
    is_male: bool,
) -> Dict[str, Any]:
    fusion = MyeongriCompleteFusion()
    run_id = (rows[0].get("run_metadata") or {}).get("run_id", "unknown")

    L_list: List[float] = []
    M_list: List[float] = []
    norm_list: List[float] = []
    err_rate: List[float] = []
    div_ratio: List[float] = []
    traffic: List[float] = []
    skipped_zero = 0

    for obj in rows:
        m = obj["metrics"]
        tr = int(m["total_requests"])
        if tr <= 0:
            skipped_zero += 1
            continue
        ec = int(m["error_count"])
        ut = int(m["unique_trace_ids"])
        dt = _parse_window_start_utc(str(obj["window_start_utc"]))
        doc = fusion.calculate_complete_fusion(
            dt.year,
            dt.month,
            dt.day,
            dt.hour,
            is_solar=is_solar,
            is_male=is_male,
        )
        v = doc["vector_4d"]
        L_list.append(float(v["L"]))
        M_list.append(float(v["M"]))
        norm_list.append(_l2_norm(v))
        err_rate.append(ec / tr)
        div_ratio.append(ut / tr)
        traffic.append(float(tr))

    n = len(L_list)
    reason: Optional[str] = None
    if n < min_valid_windows:
        reason = f"valid_windows={n} < min_valid_windows={min_valid_windows}"

    null_block = {
        "pearson": None,
        "spearman": None,
        "p_value_pearson": None,
        "p_value_spearman": None,
        "valid_windows": n,
        "skipped_windows_zero_requests": skipped_zero,
        "aborted_reason": reason,
    }

    if n < min_valid_windows:
        results = {
            "L_axis_vs_error_rate": dict(null_block),
            "M_axis_vs_diversity": dict(null_block),
            "L2_norm_vs_total_requests": dict(null_block),
        }
    else:
        results = {
            "L_axis_vs_error_rate": {
                **_correlation_block(L_list, err_rate),
                "skipped_windows_zero_requests": skipped_zero,
                "aborted_reason": None,
            },
            "M_axis_vs_diversity": {
                **_correlation_block(M_list, div_ratio),
                "skipped_windows_zero_requests": skipped_zero,
                "aborted_reason": None,
            },
            "L2_norm_vs_total_requests": {
                **_correlation_block(norm_list, traffic),
                "skipped_windows_zero_requests": skipped_zero,
                "aborted_reason": None,
            },
        }

    return {
        "schema": OUTPUT_SCHEMA,
        "version": "0.1.0",
        "run_id": run_id,
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "labels": ["[HYPO]", "[NON-DETERMINISTIC]", "[NON-MEDICAL]"],
        "disclaimer": (
            "This correlation is an observational hypothesis and MUST NOT be used for "
            "automated routing or production gating."
        ),
        "manifest": {
            "input_schema": INPUT_SCHEMA,
            "min_valid_windows": min_valid_windows,
            "timezone_policy": "window_start_utc interpreted as UTC wall clock y/m/d/hour",
            "myeongri_pipeline": "scripts.myeongri_complete_fusion.MyeongriCompleteFusion",
            "projection_4d": "tools.core.myeongri_4d_correction._ohang_data_to_4d",
            "is_solar": is_solar,
            "is_male": is_male,
            "pairs_contract": {
                "L_axis_vs_error_rate": "L (fire-weight axis) vs error_count/total_requests",
                "M_axis_vs_diversity": "M (earth+water condensed) vs unique_trace_ids/total_requests",
                "L2_norm_vs_total_requests": "L2 norm of (S,L,K,M) vs total_requests",
            },
        },
        "results": results,
    }


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, required=True, help="Path to JSONL input")
    p.add_argument(
        "--output",
        type=Path,
        default=_WS / "docs" / "final" / "artifacts" / "log_myeongri_correlation_latest.json",
    )
    p.add_argument("--stdout-only", action="store_true")
    p.add_argument("--min-valid-windows", type=int, default=MIN_VALID_WINDOWS_DEFAULT)
    p.add_argument("--solar", action="store_true", default=True)
    p.add_argument("--no-solar", action="store_false", dest="solar")
    p.add_argument("--male", action="store_true", default=True)
    p.add_argument("--female", action="store_false", dest="male")
    return p.parse_args()


def main() -> int:
    args = _parse_args()
    inp = args.input.resolve()
    if not inp.is_file():
        print(f"ERROR: input not found: {inp}", file=sys.stderr)
        return 2

    rows: List[Dict[str, Any]] = []
    for i, line in enumerate(inp.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        _validate_input_row(obj, i)
        rows.append(obj)

    if not rows:
        print("ERROR: no JSONL rows", file=sys.stderr)
        return 2

    run_ids = {(r.get("run_metadata") or {}).get("run_id") for r in rows}
    if len(run_ids) > 1:
        print(f"WARNING: multiple run_id values in file: {run_ids}", file=sys.stderr)

    doc = run_correlation(
        rows,
        min_valid_windows=int(args.min_valid_windows),
        is_solar=bool(args.solar),
        is_male=bool(args.male),
    )
    text = json.dumps(doc, ensure_ascii=False, indent=2)
    print(text)
    if not args.stdout_only:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
        print(f"\nWrote {args.output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
