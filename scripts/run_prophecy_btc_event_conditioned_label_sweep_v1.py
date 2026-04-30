#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PRED_SOURCE = ROOT / "docs" / "final" / "artifacts" / "btc_per_date_direction_causal_rule_select_latest.json"
DEFAULT_BTC_CSV = ROOT / "research" / "market_data" / "btc_daily_external_yf.csv"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "prophecy_btc_event_conditioned_label_sweep_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_int_csv(raw: str) -> list[int]:
    vals: list[int] = []
    for tok in raw.split(","):
        t = tok.strip()
        if not t:
            continue
        vals.append(int(t))
    return vals


def _parse_float_csv(raw: str) -> list[float]:
    vals: list[float] = []
    for tok in raw.split(","):
        t = tok.strip()
        if not t:
            continue
        vals.append(float(t))
    return vals


def _quantile(vals: list[float], q: float) -> float:
    if not vals:
        return 0.0
    s = sorted(vals)
    idx = int(max(0, min(len(s) - 1, round((len(s) - 1) * q))))
    return float(s[idx])


def _load_pred_map(path: Path) -> dict[str, str]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, str] = {}
    for r in (doc.get("rows") or []):
        if not isinstance(r, dict):
            continue
        d = str(r.get("eval_date") or "")[:10]
        p = str(r.get("predicted_direction") or "").lower()
        if d and p in ("bull", "bear", "neutral"):
            out[d] = p
    return out


def _load_btc_series(path: Path) -> tuple[list[str], dict[str, float]]:
    rows: list[tuple[str, float]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rd = csv.DictReader(f)
        for r in rd:
            rows.append((str(r["Date"])[:10], float(r["Close"])))
    rows.sort(key=lambda x: x[0])
    dates = [d for d, _ in rows]
    close = {d: c for d, c in rows}
    return dates, close


def _build_rows(
    *,
    pred_map: dict[str, str],
    dates: list[str],
    close: dict[str, float],
    horizon_days: int,
    neutral_bps: float,
    vol_q: float,
    relabel_high_vol_to_neutral: bool,
    drop_high_vol_rows: bool,
) -> list[dict[str, Any]]:
    dindex = {d: i for i, d in enumerate(dates)}
    eval_dates = [d for d in dates if d in pred_map and (dindex[d] + horizon_days) < len(dates)]

    # realized absolute return over horizon as event proxy
    abs_rets: list[float] = []
    for d in eval_dates:
        i = dindex[d]
        d2 = dates[i + horizon_days]
        c1 = close[d]
        c2 = close[d2]
        if c1 == 0:
            abs_rets.append(0.0)
        else:
            abs_rets.append(abs((c2 - c1) / c1))
    vol_cut = _quantile(abs_rets, vol_q)

    out_rows: list[dict[str, Any]] = []
    thr = neutral_bps / 10000.0
    for d in eval_dates:
        i = dindex[d]
        d2 = dates[i + horizon_days]
        c1 = close[d]
        c2 = close[d2]
        if c1 == 0:
            continue
        ret = (c2 - c1) / c1
        abs_ret = abs(ret)
        high_vol = abs_ret >= vol_cut if vol_cut > 0 else False

        if drop_high_vol_rows and high_vol:
            continue

        act = "bull" if ret > thr else ("bear" if ret < -thr else "neutral")
        if relabel_high_vol_to_neutral and high_vol:
            act = "neutral"

        out_rows.append(
            {
                "instrument": "btc",
                "eval_date": d,
                "predicted_direction": pred_map[d],
                "actual_direction": act,
                "daily_return": round(ret, 8),
                "prev_close": c1,
                "close": c2,
                "neutral_bps": neutral_bps,
                "label_horizon_days": horizon_days,
                "event_high_vol": bool(high_vol),
                "event_vol_cut_abs_ret": round(vol_cut, 8),
            }
        )
    return out_rows


def main() -> int:
    ap = argparse.ArgumentParser(description="BTC event-conditioned label sweep for strict gate.")
    ap.add_argument("--pred-source-json", type=Path, default=DEFAULT_PRED_SOURCE)
    ap.add_argument("--btc-csv", type=Path, default=DEFAULT_BTC_CSV)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--fast-grid",
        action="store_true",
        help="Single representative combo (h=2, nb=8, vq=0.9, relabel) for smoke / iteration.",
    )
    ap.add_argument("--horizon-grid", type=str, default="", help="Optional CSV override, e.g. '1,2,3'")
    ap.add_argument("--neutral-bps-grid", type=str, default="", help="Optional CSV override, e.g. '4,8,12'")
    ap.add_argument("--volq-grid", type=str, default="", help="Optional CSV override, e.g. '0.9,0.95'")
    ap.add_argument("--n-folds", type=int, default=4, help="Walk-forward folds passed to per-date combo script.")
    ap.add_argument(
        "--per-combo-timeout-sec",
        type=int,
        default=600,
        help="Timeout seconds for each walkforward/gate subprocess per combo.",
    )
    ap.add_argument(
        "--max-combos",
        type=int,
        default=0,
        help="Optional hard cap on number of combos to evaluate (0 = no cap).",
    )
    ap.add_argument(
        "--train-objective",
        type=str,
        default="accuracy",
        choices=("accuracy", "margin_vs_bull"),
        help="Walk-forward training objective passed to per-date combo script.",
    )
    ap.add_argument(
        "--mode-grid",
        type=str,
        default="",
        help="Optional CSV override of mode names: relabel,drop (e.g. 'drop' or 'relabel,drop')",
    )
    args = ap.parse_args()

    pred_src_path = args.pred_source_json if args.pred_source_json.is_absolute() else (ROOT / args.pred_source_json)
    btc_csv_path = args.btc_csv if args.btc_csv.is_absolute() else (ROOT / args.btc_csv)
    pred_map = _load_pred_map(pred_src_path)
    dates, close = _load_btc_series(btc_csv_path)
    artifacts = ROOT / "docs" / "final" / "artifacts"

    if args.fast_grid:
        horizon_grid = [2]
        neutral_grid = [8.0]
        volq_grid = [0.9]
        mode_grid = [("relabel", True, False)]
    else:
        horizon_grid = [2, 3]
        neutral_grid = [8.0, 12.0]
        volq_grid = [0.8, 0.9, 0.95]
        mode_grid = [
            ("relabel", True, False),
            ("drop", False, True),
        ]

    if args.horizon_grid.strip():
        horizon_grid = _parse_int_csv(args.horizon_grid)
    if args.neutral_bps_grid.strip():
        neutral_grid = _parse_float_csv(args.neutral_bps_grid)
    if args.volq_grid.strip():
        volq_grid = _parse_float_csv(args.volq_grid)
    if args.mode_grid.strip():
        mm = [x.strip().lower() for x in args.mode_grid.split(",") if x.strip()]
        mode_grid = []
        if "relabel" in mm:
            mode_grid.append(("relabel", True, False))
        if "drop" in mm:
            mode_grid.append(("drop", False, True))

    all_combos: list[tuple[int, float, float, str, bool, bool]] = []
    for h in horizon_grid:
        for nb in neutral_grid:
            for vq in volq_grid:
                for mode_name, relabel, drop in mode_grid:
                    all_combos.append((h, nb, vq, mode_name, relabel, drop))
    if int(args.max_combos) > 0:
        all_combos = all_combos[: int(args.max_combos)]
    total = len(all_combos)

    results: list[dict[str, Any]] = []
    for idx, (h, nb, vq, mode_name, relabel, drop) in enumerate(all_combos, start=1):
        tag = f"h{h}_nb{str(nb).replace('.', 'p')}_vq{str(vq).replace('.', 'p')}_{mode_name}"
        print(f"[{idx}/{total}] START {tag}", flush=True)
        rows = _build_rows(
            pred_map=pred_map,
            dates=dates,
            close=close,
            horizon_days=h,
            neutral_bps=nb,
            vol_q=vq,
            relabel_high_vol_to_neutral=relabel,
            drop_high_vol_rows=drop,
        )
        rows = rows[-1200:]
        if len(rows) < 400:
            print(f"[{idx}/{total}] SKIP {tag} rows={len(rows)}", flush=True)
            continue

        score_path = artifacts / f"btrack_prophecy_score_btc_event_{tag}_latest.json"
        wf_path = artifacts / f"prophecy_per_date_combo_walkforward_btc_event_{tag}_latest.json"
        gate_path = artifacts / f"prophecy_production_gate_strict_btc_event_{tag}_latest.json"
        payload = {
            "schema": "btrack_prophecy_score_v1",
            "generated_at_utc": _utc_now(),
            "research_only": True,
            "rows": rows,
            "inputs": {
                "pred_source_json": str(pred_src_path.relative_to(ROOT)),
                "btc_csv": str(btc_csv_path.relative_to(ROOT)),
                "kospi_csv": str((ROOT / "research" / "market_data" / "kospi_daily_external_yf.csv").relative_to(ROOT)),
                "label_horizon_days": h,
                "neutral_bps": nb,
                "event_mode": mode_name,
                "event_vol_quantile": vq,
            },
        }
        score_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        try:
            r1 = subprocess.run(
                [
                    "py",
                    "scripts/run_prophecy_per_date_combo_walkforward_v1.py",
                    "--score-json",
                    str(score_path),
                    "--target-instrument",
                    "btc",
                    "--train-objective",
                    str(args.train_objective),
                    "--n-folds",
                    str(int(args.n_folds)),
                    "--include-source-direction-signal",
                    "--include-expanded-prior-features",
                    "--output",
                    str(wf_path),
                ],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                timeout=max(30, int(args.per_combo_timeout_sec)),
            )
        except subprocess.TimeoutExpired:
            results.append({"tag": tag, "ok": False, "stage": "walkforward_timeout", "error": "timeout"})
            print(f"[{idx}/{total}] TIMEOUT walkforward {tag}", flush=True)
            continue
        if r1.returncode != 0:
            results.append({"tag": tag, "ok": False, "stage": "walkforward", "error": (r1.stderr or r1.stdout)[:240]})
            print(f"[{idx}/{total}] FAIL walkforward {tag}", flush=True)
            continue

        try:
            r2 = subprocess.run(
                [
                    "py",
                    "scripts/eval_prophecy_promotion_gates_v1.py",
                    "--lens-walkforward-json",
                    str(wf_path),
                    "--instrument-walkforward-json",
                    str(artifacts / "prophecy_instrument_combo_walkforward_strictrefresh_latest.json"),
                    "--score-json",
                    str(score_path),
                    "--promotion-track-mode",
                    "btc_only_crossassist",
                    "--min-mean",
                    "0.55",
                    "--max-stdev",
                    "0.15",
                    "--min-beat-bull-frac",
                    "0.5",
                    "--min-worst-fold",
                    "0.4",
                    "--strict-streak-required",
                    "1",
                    "--streak-history-json",
                    str(artifacts / "prophecy_promotion_strict_streak_legacy_v1.json"),
                    "--output",
                    str(gate_path),
                ],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                timeout=max(30, int(args.per_combo_timeout_sec)),
            )
        except subprocess.TimeoutExpired:
            results.append({"tag": tag, "ok": False, "stage": "gate_timeout", "error": "timeout"})
            print(f"[{idx}/{total}] TIMEOUT gate {tag}", flush=True)
            continue
        if r2.returncode != 0:
            results.append({"tag": tag, "ok": False, "stage": "gate", "error": (r2.stderr or r2.stdout)[:240]})
            print(f"[{idx}/{total}] FAIL gate {tag}", flush=True)
            continue

        g = json.loads(gate_path.read_text(encoding="utf-8"))
        obs = {x["gate_id"]: x.get("observed", {}) for x in (g.get("gates") or []) if isinstance(x, dict) and "gate_id" in x}
        results.append(
            {
                "tag": tag,
                "ok": True,
                "h": h,
                "neutral_bps": nb,
                "vol_q": vq,
                "mode": mode_name,
                "mean_test_accuracy": float((obs.get("lens_wf_mean_test_accuracy", {}) or {}).get("mean_test_accuracy", 0.0)),
                "stdev_test_accuracy": float((obs.get("lens_wf_stdev_test_accuracy", {}) or {}).get("stdev_test_accuracy", 1.0)),
                "fraction_test_beats_always_bull": float(
                    (obs.get("lens_wf_fraction_folds_beat_always_bull", {}) or {}).get("fraction_test_beats_always_bull", 0.0)
                ),
                "min_test_accuracy": float((obs.get("lens_wf_min_fold_test_accuracy", {}) or {}).get("min_test_accuracy", 0.0)),
                "strict_passed": bool(g.get("strict_passed")),
                "all_gates_passed": bool(g.get("all_gates_passed")),
                "gate_json": str(gate_path),
            }
        )
        print(f"[{idx}/{total}] DONE {tag}", flush=True)

    ok = [r for r in results if r.get("ok")]
    ok.sort(key=lambda x: x.get("mean_test_accuracy", 0.0), reverse=True)
    out = {
        "schema": "prophecy_btc_event_conditioned_label_sweep_v1",
        "generated_at_utc": _utc_now(),
        "best": ok[0] if ok else None,
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    if ok:
        print("BEST:", json.dumps(ok[0], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

