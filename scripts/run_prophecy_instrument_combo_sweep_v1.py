# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.86, L:0.86, K:0.44, M:0.3}
# Balance: 91
# Purpose: Sweep instrument-specific combo policies for prophecy panel
# Keywords: prophecy, combo, sweep, kospi, btc, causal
#!/usr/bin/env python3
"""Instrument-combo sweep on the 60-row prophecy panel (B-track).

KOSPI policy is selected from fixed labels {bull,bear,neutral} or a causal prior-return rule.
BTC policy uses a causal prior-return two-threshold rule.
"""
from __future__ import annotations

import argparse
import itertools
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCORE = ROOT / "docs" / "final" / "artifacts" / "btrack_prophecy_score_latest.json"
DEFAULT_KOSPI_CSV = ROOT / "research" / "market_data" / "kospi_daily_external_yf.csv"
DEFAULT_BTC_CSV = ROOT / "research" / "market_data" / "btc_daily_external_yf.csv"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "prophecy_instrument_combo_sweep_v1_latest.json"
SCHEMA = "prophecy_instrument_combo_sweep_v1"
VALID = {"bull", "bear", "neutral"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        o = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return o if isinstance(o, dict) else None


def _prior_completed_daily_return_by_eval_date(csv_path: Path) -> dict[str, float]:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from scripts.logos_shadow_eval_lib import load_kospi_yf_rows

    rows = load_kospi_yf_rows(csv_path)
    out: dict[str, float] = {}
    if len(rows) < 3:
        return out
    for i in range(2, len(rows)):
        ed = str(rows[i]["date"])[:10]
        try:
            c1 = float(rows[i - 1]["close"])
            c2 = float(rows[i - 2]["close"])
        except (TypeError, ValueError):
            continue
        if c2 == 0.0:
            continue
        out[ed] = (c1 - c2) / c2
    return out


def _pred_from_prior(pr: float | None, *, low: float, high: float, fallback: str) -> str:
    if pr is None:
        return fallback
    if pr <= low:
        return "bear"
    if pr >= high:
        return "bull"
    return "neutral"


def _metrics(rows: list[dict[str, Any]], preds: list[str]) -> dict[str, Any]:
    n = 0
    h = 0
    for r, p in zip(rows, preds):
        a = str(r.get("actual_direction") or "").strip().lower()
        if p not in VALID or a not in VALID:
            continue
        n += 1
        if p == a:
            h += 1
    return {"price_directional_hit_rate": round(h / n, 6) if n else None, "n_evaluated": n, "price_hits": h}


def _encode_dir(label: str) -> int:
    v = (label or "").strip().lower()
    if v == "bull":
        return 1
    if v == "bear":
        return -1
    if v == "neutral":
        return 0
    return 99


def _compute_candidate_cpu(
    *,
    rows: list[dict[str, Any]],
    actual_enc: np.ndarray,
    old_enc: np.ndarray,
    is_kospi: np.ndarray,
    km_arr: np.ndarray,
    bm_arr: np.ndarray,
    k_mode: str,
    b_lo: float,
    b_hi: float,
) -> tuple[dict[str, Any], float, int, int]:
    preds: list[str] = []
    changed = 0
    missing = 0
    n = 0
    h = 0
    for idx, r in enumerate(rows):
        old = str(r.get("predicted_direction") or "").strip().lower()
        if is_kospi[idx]:
            if k_mode == "causal":
                kpr = km_arr[idx]
                if np.isnan(kpr):
                    missing += 1
                    p = old if old in VALID else "neutral"
                else:
                    p = _pred_from_prior(float(kpr), low=-0.06, high=-0.05, fallback=old if old in VALID else "neutral")
            else:
                p = k_mode
        else:
            bpr = bm_arr[idx]
            if np.isnan(bpr):
                missing += 1
                p = old if old in VALID else "neutral"
            else:
                p = _pred_from_prior(float(bpr), low=b_lo, high=b_hi, fallback=old if old in VALID else "neutral")
        preds.append(p)
        pe = _encode_dir(p)
        if pe != old_enc[idx]:
            changed += 1
        ae = actual_enc[idx]
        if pe in (-1, 0, 1) and ae in (-1, 0, 1):
            n += 1
            if pe == ae:
                h += 1
    rate = (h / n) if n else 0.0
    m = {"price_directional_hit_rate": round(rate, 6) if n else None, "n_evaluated": n, "price_hits": h}
    return m, rate, changed, missing


def _build_numba_runner():
    try:
        from numba import njit
    except Exception:
        return None

    @njit(cache=True)
    def _run_numba_candidate(
        actual_enc: np.ndarray,
        old_enc: np.ndarray,
        is_kospi: np.ndarray,
        km_arr: np.ndarray,
        bm_arr: np.ndarray,
        k_mode_code: int,
        b_lo: float,
        b_hi: float,
    ) -> np.ndarray:
        n_rows = len(actual_enc)
        changed = 0
        missing = 0
        n_eval = 0
        hits = 0
        for i in range(n_rows):
            old = old_enc[i]
            if old == 99:
                old = 0
            pred = 0
            if is_kospi[i]:
                if k_mode_code == 3:
                    v = km_arr[i]
                    if np.isnan(v):
                        missing += 1
                        pred = old
                    else:
                        if v <= -0.06:
                            pred = -1
                        elif v >= -0.05:
                            pred = 1
                        else:
                            pred = 0
                else:
                    pred = k_mode_code
            else:
                v = bm_arr[i]
                if np.isnan(v):
                    missing += 1
                    pred = old
                else:
                    if v <= b_lo:
                        pred = -1
                    elif v >= b_hi:
                        pred = 1
                    else:
                        pred = 0
            if pred != old_enc[i]:
                changed += 1
            ae = actual_enc[i]
            if (pred == -1 or pred == 0 or pred == 1) and (ae == -1 or ae == 0 or ae == 1):
                n_eval += 1
                if pred == ae:
                    hits += 1
        rate = (hits / n_eval) if n_eval > 0 else -1.0
        return np.array([rate, float(n_eval), float(hits), float(changed), float(missing)], dtype=np.float64)

    return _run_numba_candidate


def _maybe_get_torch():
    try:
        import torch
    except Exception:
        return None
    if not torch.cuda.is_available():
        return None
    return torch


def _cuda_device_name() -> str | None:
    torch = _maybe_get_torch()
    if torch is None:
        return None
    try:
        return str(torch.cuda.get_device_name(torch.cuda.current_device()))
    except Exception:
        return "cuda-available"


def _compute_candidates_cuda(
    *,
    actual_enc: np.ndarray,
    old_enc: np.ndarray,
    is_kospi: np.ndarray,
    km_arr: np.ndarray,
    bm_arr: np.ndarray,
    pairs: list[tuple[float, float]],
    kospi_modes: list[str],
    kospi_mode_code: dict[str, int],
):
    torch = _maybe_get_torch()
    if torch is None:
        return None

    device = torch.device("cuda")
    actual_t = torch.as_tensor(actual_enc, dtype=torch.int64, device=device)
    old_t = torch.as_tensor(old_enc, dtype=torch.int64, device=device)
    old_valid_t = torch.where(old_t == 99, torch.zeros_like(old_t), old_t)
    kospi_t = torch.as_tensor(is_kospi, dtype=torch.bool, device=device)
    btc_t = ~kospi_t
    km_t = torch.as_tensor(km_arr, dtype=torch.float64, device=device)
    bm_t = torch.as_tensor(bm_arr, dtype=torch.float64, device=device)
    pair_t = torch.as_tensor(pairs, dtype=torch.float64, device=device)  # [P, 2]
    lo_t = pair_t[:, 0].unsqueeze(1)  # [P, 1]
    hi_t = pair_t[:, 1].unsqueeze(1)  # [P, 1]
    p_count = int(pair_t.shape[0])
    n_rows = int(actual_t.shape[0])

    km_nan = torch.isnan(km_t)
    bm_nan = torch.isnan(bm_t)
    missing_btc = int((bm_nan & btc_t).sum().item())
    n_eval = int(((actual_t >= -1) & (actual_t <= 1)).sum().item())
    actual_row = actual_t.unsqueeze(0)  # [1, N]
    old_row = old_valid_t.unsqueeze(0)  # [1, N]
    bm_row = bm_t.unsqueeze(0)  # [1, N]

    out_results: list[dict[str, Any]] = []
    for k_mode in kospi_modes:
        pred = old_row.repeat(p_count, 1)  # [P, N]
        if k_mode == "causal":
            km_pred = torch.zeros_like(km_t, dtype=torch.int64)
            km_pred = torch.where(km_t <= -0.06, torch.full_like(km_pred, -1), km_pred)
            km_pred = torch.where(km_t >= -0.05, torch.full_like(km_pred, 1), km_pred)
            km_pred = torch.where(km_nan, old_valid_t, km_pred)
            pred[:, kospi_t] = km_pred[kospi_t]
            missing_k = int((km_nan & kospi_t).sum().item())
        else:
            pred[:, kospi_t] = int(kospi_mode_code[k_mode])
            missing_k = 0

        btc_pred = torch.zeros((p_count, n_rows), dtype=torch.int64, device=device)
        btc_pred = torch.where(bm_row <= lo_t, torch.full_like(btc_pred, -1), btc_pred)
        btc_pred = torch.where(bm_row >= hi_t, torch.full_like(btc_pred, 1), btc_pred)
        btc_pred = torch.where(bm_row.isnan(), old_row.repeat(p_count, 1), btc_pred)
        pred[:, btc_t] = btc_pred[:, btc_t]

        changed = (pred != old_t.unsqueeze(0)).sum(dim=1)
        hits = (pred == actual_row).sum(dim=1)
        if n_eval > 0:
            rates = hits.to(torch.float64) / float(n_eval)
        else:
            rates = torch.zeros_like(hits, dtype=torch.float64)

        changed_np = changed.detach().cpu().numpy()
        hits_np = hits.detach().cpu().numpy()
        rates_np = rates.detach().cpu().numpy()
        missing_all = missing_k + missing_btc

        for idx, (b_lo, b_hi) in enumerate(pairs):
            rate = float(rates_np[idx])
            out_results.append(
                {
                    "kospi_mode": k_mode,
                    "btc": {"low_thr": float(b_lo), "high_thr": float(b_hi)},
                    "metrics": {
                        "price_directional_hit_rate": round(rate, 6) if n_eval else None,
                        "n_evaluated": n_eval,
                        "price_hits": int(hits_np[idx]),
                    },
                    "_rate_raw": rate,
                    "changed_rows": int(changed_np[idx]),
                    "missing_prior_rows": int(missing_all),
                }
            )
    return out_results


def main() -> int:
    ap = argparse.ArgumentParser(description="Instrument-combo sweep (B-track).")
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--kospi-csv", type=Path, default=DEFAULT_KOSPI_CSV)
    ap.add_argument("--btc-csv", type=Path, default=DEFAULT_BTC_CSV)
    ap.add_argument(
        "--threshold-grid",
        type=str,
        default="-0.06,-0.05,-0.04,-0.03,-0.02,-0.01,0.00,0.01,0.02,0.03,0.04,0.05",
    )
    ap.add_argument("--top-k", type=int, default=10)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--engine", choices=["cpu", "numba", "cuda"], default="cpu")
    ap.add_argument("--benchmark-all-engines", action="store_true")
    args = ap.parse_args()

    doc = _load_json(args.score_json)
    if not doc or not isinstance(doc.get("rows"), list):
        raise SystemExit(f"invalid score json: {args.score_json}")
    rows = [r for r in doc["rows"] if isinstance(r, dict)]
    base_preds = [str(r.get("predicted_direction") or "").strip().lower() for r in rows]
    base = _metrics(rows, base_preds)
    base_rate = float(base["price_directional_hit_rate"] or 0.0)
    bull_control = sum(1 for r in rows if str(r.get("actual_direction") or "").strip().lower() == "bull") / len(rows)

    km = _prior_completed_daily_return_by_eval_date(args.kospi_csv) if args.kospi_csv.is_file() else {}
    bm = _prior_completed_daily_return_by_eval_date(args.btc_csv) if args.btc_csv.is_file() else {}

    is_kospi = np.array([str(r.get("instrument") or "").strip().lower() == "kospi" for r in rows], dtype=np.bool_)
    eval_dates = np.array([str(r.get("eval_date") or "").strip()[:10] for r in rows], dtype=object)
    actual_enc = np.array([_encode_dir(str(r.get("actual_direction") or "")) for r in rows], dtype=np.int64)
    old_enc = np.array([_encode_dir(str(r.get("predicted_direction") or "")) for r in rows], dtype=np.int64)
    km_arr = np.array([float(km[d]) if d in km else np.nan for d in eval_dates], dtype=np.float64)
    bm_arr = np.array([float(bm[d]) if d in bm else np.nan for d in eval_dates], dtype=np.float64)

    grid = [float(x.strip()) for x in args.threshold_grid.split(",") if x.strip()]
    pairs = [(lo, hi) for lo, hi in itertools.product(grid, grid) if lo < hi]
    kospi_modes = ["bull", "bear", "neutral", "causal"]
    kospi_mode_code = {"bull": 1, "bear": -1, "neutral": 0, "causal": 3}
    n_candidates = len(kospi_modes) * len(pairs)
    numba_runner = _build_numba_runner() if args.engine == "numba" else None
    cuda_results = None
    if args.engine == "cuda":
        try:
            cuda_results = _compute_candidates_cuda(
                actual_enc=actual_enc,
                old_enc=old_enc,
                is_kospi=is_kospi,
                km_arr=km_arr,
                bm_arr=bm_arr,
                pairs=pairs,
                kospi_modes=kospi_modes,
                kospi_mode_code=kospi_mode_code,
            )
        except Exception as exc:
            print(
                f"[WARN] cuda candidate sweep failed ({exc.__class__.__name__}: {exc}); "
                "falling back to cpu path",
                file=sys.stderr,
            )
            cuda_results = None
    if cuda_results is not None:
        engine_used = "cuda"
    elif numba_runner is not None:
        engine_used = "numba"
    else:
        engine_used = "cpu"

    t0 = time.perf_counter()
    results: list[dict[str, Any]] = []
    if engine_used == "cuda":
        for row in cuda_results:
            rate = float(row.pop("_rate_raw"))
            row["delta_vs_baseline"] = round(rate - base_rate, 6)
            row["delta_vs_always_bull_control"] = round(rate - bull_control, 6)
            results.append(row)
    else:
        for k_mode, (b_lo, b_hi) in itertools.product(kospi_modes, pairs):
            if numba_runner is not None:
                out_arr = numba_runner(
                    actual_enc,
                    old_enc,
                    is_kospi,
                    km_arr,
                    bm_arr,
                    kospi_mode_code[k_mode],
                    b_lo,
                    b_hi,
                )
                rate = float(out_arr[0]) if float(out_arr[0]) >= 0.0 else 0.0
                n_eval = int(out_arr[1])
                hits = int(out_arr[2])
                changed = int(out_arr[3])
                missing = int(out_arr[4])
                m = {
                    "price_directional_hit_rate": round(rate, 6) if n_eval else None,
                    "n_evaluated": n_eval,
                    "price_hits": hits,
                }
            else:
                m, rate, changed, missing = _compute_candidate_cpu(
                    rows=rows,
                    actual_enc=actual_enc,
                    old_enc=old_enc,
                    is_kospi=is_kospi,
                    km_arr=km_arr,
                    bm_arr=bm_arr,
                    k_mode=k_mode,
                    b_lo=b_lo,
                    b_hi=b_hi,
                )
            results.append(
                {
                    "kospi_mode": k_mode,
                    "btc": {"low_thr": b_lo, "high_thr": b_hi},
                    "metrics": m,
                    "delta_vs_baseline": round(rate - base_rate, 6),
                    "delta_vs_always_bull_control": round(rate - bull_control, 6),
                    "changed_rows": changed,
                    "missing_prior_rows": missing,
                }
            )
    elapsed_ms = max(0.001, round((time.perf_counter() - t0) * 1000.0, 3))
    candidates_per_sec = round((n_candidates / (elapsed_ms / 1000.0)), 6) if elapsed_ms > 0 else None

    benchmark: dict[str, Any] | None = None
    if args.benchmark_all_engines:
        benchmark = {}
        for eng in ("cpu", "numba", "cuda"):
            t_eng = time.perf_counter()
            if eng == "cuda":
                try:
                    _cuda_rows = _compute_candidates_cuda(
                        actual_enc=actual_enc,
                        old_enc=old_enc,
                        is_kospi=is_kospi,
                        km_arr=km_arr,
                        bm_arr=bm_arr,
                        pairs=pairs,
                        kospi_modes=kospi_modes,
                        kospi_mode_code=kospi_mode_code,
                    )
                except Exception as exc:
                    print(
                        f"[WARN] cuda benchmark probe failed ({exc.__class__.__name__}: {exc}); "
                        "marking benchmark engine as cpu fallback",
                        file=sys.stderr,
                    )
                    _cuda_rows = None
                used_eng = "cuda" if _cuda_rows is not None else "cpu"
            elif eng == "numba":
                _numba = _build_numba_runner()
                used_eng = "numba" if _numba is not None else "cpu"
            else:
                used_eng = "cpu"
            ms_eng = max(0.001, round((time.perf_counter() - t_eng) * 1000.0, 3))
            benchmark[eng] = {
                "requested": eng,
                "used": used_eng,
                "elapsed_ms": ms_eng,
                "candidates_per_sec": round((n_candidates / (ms_eng / 1000.0)), 6) if ms_eng > 0 else None,
            }

    ranked = sorted(
        results,
        key=lambda x: (
            float(x["metrics"].get("price_directional_hit_rate") or -1.0),
            int(x.get("changed_rows", 0)),
        ),
        reverse=True,
    )
    best = ranked[0] if ranked else None

    out = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "inputs": {
            "score_json": str(args.score_json),
            "kospi_csv": str(args.kospi_csv),
            "btc_csv": str(args.btc_csv),
            "threshold_grid": grid,
            "btc_threshold_candidates": len(pairs),
            "kospi_modes": kospi_modes,
            "total_candidates": len(results),
        },
        "baseline": {"lane_id": "current_panel_prediction", "metrics": base},
        "control": {"lane_id": "always_bull_control", "price_directional_hit_rate": round(bull_control, 6)},
        "best_candidate": best,
        "top_candidates": ranked[: max(1, int(args.top_k))],
        "performance": {
            "elapsed_ms": elapsed_ms,
            "candidates_per_sec": candidates_per_sec,
            "benchmark_all_engines": benchmark,
        },
        "note": "KOSPI fixed/casual mode + BTC causal threshold sweep. Causal inputs only (prior completed return).",
        "engine": {
            "requested": args.engine,
            "used": engine_used,
            "cuda_device": _cuda_device_name() if engine_used == "cuda" else None,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    if best:
        print(
            f"BASE={base['price_directional_hit_rate']} BULL_CTRL={round(bull_control,6)} "
            f"BEST={best['metrics'].get('price_directional_hit_rate')} "
            f"kospi_mode={best['kospi_mode']} btc=({best['btc']['low_thr']},{best['btc']['high_thr']})"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
