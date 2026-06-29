#!/usr/bin/env python3
"""[HYPO] RQ-026 KOSPI TSFM stack ensemble walk-forward shadow (B-track, research_only).

Combines Chronos-2, TimesFM 2.5, and Moirai-2 median quantile on the same 252d
blocked WF panel (5bps neutral). Arms: majority vote, unanimous vote, Moirai
quantile-band agreement, mom20d hybrid, anti-bull-bias guard fallback.

Does not mutate Track A, operational prophecy JSON, or live trading hooks.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_rq025_chronos2_kospi_daily_wf_shadow_v1 import (  # noqa: E402
    _blocked_folds,
    _chronos2_median_next_close,
    _chronos2_probe,
    _load_chronos2_pipeline,
)
from scripts.run_rq025_moirai2_kospi_daily_wf_shadow_v1 import (  # noqa: E402
    _actual_direction,
    _load_closes,
    _load_moirai2_predictor,
    _moirai_probe,
    _mom_pred,
)
from scripts.run_rq025_timesfm25_kospi_daily_wf_shadow_v1 import (  # noqa: E402
    _load_timesfm_model,
    _timesfm_probe,
)

DEFAULT_KOSPI = ROOT / "research/market_data/kospi_daily_external_yf.csv"
DEFAULT_OUT = ROOT / "reports/rq026_kospi_tsfm_stack_ensemble_wf_shadow_v1_latest.json"
DEFAULT_POINTER = ROOT / "reports/rq026_tsfm_stack_research_v1_latest.json"
DEFAULT_WF = ROOT / "reports/kospi_prophecy_wf_holdout_compare_v1_latest.json"
DEFAULT_RQ025 = ROOT / "reports/rq025_tsfm_delta_arms_v1_latest.json"
SCHEMA = "rq026_kospi_tsfm_stack_ensemble_wf_shadow_v1"


def _env_bootstrap() -> None:
    os.environ.setdefault("TRANSFORMERS_NO_TF", "1")
    os.environ.setdefault("USE_TF", "0")


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        o = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return None
    return o if isinstance(o, dict) else None


def _majority_label(train_dates: list[str], actuals: dict[str, str]) -> str:
    c: Counter[str] = Counter()
    for d in train_dates:
        a = actuals.get(d)
        if a in ("bull", "bear", "neutral"):
            c[a] += 1
    return c.most_common(1)[0][0] if c else "neutral"


def _hit_from_pairs(pairs: list[tuple[str, str]]) -> dict[str, Any]:
    hits = n = 0
    dist: Counter[str] = Counter()
    for pred, act in pairs:
        if pred not in ("bull", "bear", "neutral") or act not in ("bull", "bear", "neutral"):
            continue
        if act == "neutral" and pred == "neutral":
            continue
        if act == "neutral" or pred == "neutral":
            continue
        n += 1
        dist[pred] += 1
        if pred == act:
            hits += 1
    return {
        "directional_hit_rate": round(hits / n, 6) if n else None,
        "n_evaluated": n,
        "price_hits": hits,
        "pred_distribution": dict(dist),
        "pred_bull_share": round(dist.get("bull", 0) / n, 4) if n else None,
    }


def _aggregate(folds: list[dict[str, Any]]) -> dict[str, Any]:
    rates = [f["directional_hit_rate"] for f in folds if f.get("directional_hit_rate") is not None]
    total_n = sum(int(f.get("n_evaluated") or 0) for f in folds)
    total_hits = sum(int(f.get("price_hits") or 0) for f in folds)
    return {
        "mean_test_directional_hit_rate": round(sum(rates) / len(rates), 6) if rates else None,
        "pooled_test_directional_hit_rate": round(total_hits / total_n, 6) if total_n else None,
        "fold_hit_rates": rates,
        "total_n_evaluated": total_n,
        "total_price_hits": total_hits,
        "n_folds_scored": len(rates),
        "folds": folds,
    }


def _vote_majority(preds: list[str]) -> str:
    directional = [p for p in preds if p in ("bull", "bear")]
    if not directional:
        return "neutral"
    c = Counter(directional)
    top, cnt = c.most_common(1)[0]
    if cnt >= 2:
        return top
    return "neutral"


def _vote_unanimous(preds: list[str]) -> str | None:
    directional = [p for p in preds if p in ("bull", "bear")]
    if len(directional) != len(preds) or len(set(directional)) != 1:
        return None
    return directional[0]


def _moirai_band_pred(c0: float, q10: float, q50: float, q90: float, neutral_bps: float) -> str | None:
    if c0 == 0.0:
        return None
    r10 = (q10 - c0) / c0
    r50 = (q50 - c0) / c0
    r90 = (q90 - c0) / c0
    if (r10 > 0 and r90 < 0) or (r10 < 0 and r90 > 0):
        return None
    d50 = _actual_direction(r50, neutral_bps)
    if d50 not in ("bull", "bear"):
        return None
    d10 = _actual_direction(r10, neutral_bps)
    d90 = _actual_direction(r90, neutral_bps)
    if d10 == d50 == d90:
        return d50
    return None


def _collect_fold_rows(
    *,
    closes: list[float],
    dates: list[str],
    date_to_idx: dict[str, int],
    train: list[str],
    test: list[str],
    neutral_bps: float,
    chronos_pipe: Any | None,
    timesfm_model: Any | None,
    moirai_predictor: Any | None,
    chronos_context: int,
    timesfm_context: int,
    moirai_context: int,
    moirai_batch: int,
) -> dict[str, list[tuple[str, str]]]:
    import numpy as np
    import pandas as pd

    actuals: dict[str, str] = {}
    meta: list[dict[str, Any]] = []

    for d in test:
        i = date_to_idx.get(d)
        if i is None or i < 1:
            continue
        c0 = closes[i - 1]
        c1 = closes[i]
        if c0 == 0.0:
            continue
        ret = (c1 - c0) / c0
        if abs(ret) > 0.15:
            continue
        act = _actual_direction(ret, neutral_bps)
        actuals[d] = act
        meta.append({"i": i, "date": d, "act": act, "c0": c0})

    chronos_preds: dict[str, str] = {}
    if chronos_pipe is not None:
        for row in meta:
            i = row["i"]
            pred_close = _chronos2_median_next_close(
                chronos_pipe, closes[:i], context_length=chronos_context
            )
            if pred_close is None:
                continue
            chronos_preds[row["date"]] = _actual_direction((pred_close - row["c0"]) / row["c0"], neutral_bps)

    timesfm_preds: dict[str, str] = {}
    if timesfm_model is not None and meta:
        contexts: list[Any] = []
        keys: list[str] = []
        for row in meta:
            ctx = closes[: row["i"]]
            if timesfm_context > 0 and len(ctx) > timesfm_context:
                ctx = ctx[-timesfm_context:]
            if len(ctx) < 2:
                continue
            contexts.append(np.asarray(ctx, dtype=np.float64))
            keys.append(row["date"])
        if contexts:
            point_forecast, _q = timesfm_model.forecast(horizon=1, inputs=contexts)
            for j, dkey in enumerate(keys):
                row = next(m for m in meta if m["date"] == dkey)
                pred_close = float(point_forecast[j, 0])
                timesfm_preds[dkey] = _actual_direction(
                    (pred_close - row["c0"]) / row["c0"], neutral_bps
                )

    moirai_median: dict[str, str] = {}
    moirai_band: dict[str, str] = {}
    if moirai_predictor is not None and meta:
        entries: list[dict[str, Any]] = []
        mkeys: list[str] = []
        for row in meta:
            i = row["i"]
            ctx = closes[:i]
            if moirai_context > 0 and len(ctx) > moirai_context:
                ctx = ctx[-moirai_context:]
            if len(ctx) < 2:
                continue
            start_idx = max(0, i - len(ctx))
            entries.append(
                {
                    "target": np.asarray(ctx, dtype=np.float32),
                    "start": pd.Period(dates[start_idx], freq="D"),
                }
            )
            mkeys.append(row["date"])
        forecasts: list[Any] = []
        for off in range(0, len(entries), moirai_batch):
            forecasts.extend(list(moirai_predictor.predict(entries[off : off + moirai_batch])))
        for j, dkey in enumerate(mkeys):
            row = next(m for m in meta if m["date"] == dkey)
            fc = forecasts[j]
            q10 = float(fc.quantile(0.1)[0])
            q50 = float(fc.quantile(0.5)[0])
            q90 = float(fc.quantile(0.9)[0])
            moirai_median[dkey] = _actual_direction((q50 - row["c0"]) / row["c0"], neutral_bps)
            band = _moirai_band_pred(row["c0"], q10, q50, q90, neutral_bps)
            if band is not None:
                moirai_band[dkey] = band

    train_actuals: dict[str, str] = {}
    for d in train:
        i = date_to_idx.get(d)
        if i is None or i < 1:
            continue
        c0, c1 = closes[i - 1], closes[i]
        if c0 == 0.0:
            continue
        ret = (c1 - c0) / c0
        if abs(ret) > 0.15:
            continue
        train_actuals[d] = _actual_direction(ret, neutral_bps)
    maj_train = _majority_label(train, train_actuals)

    arm_pairs: dict[str, list[tuple[str, str]]] = {
        "train_majority_baseline": [],
        "tsfm_majority_vote_2of3": [],
        "tsfm_unanimous_3of3": [],
        "moirai_quantile_band_agree": [],
        "hybrid_mom20d_plus_tsfm_majority": [],
        "anti_bull_bias_guard_stack": [],
    }

    for row in meta:
        d, act, i = row["date"], row["act"], row["i"]
        c_preds = [
            chronos_preds.get(d, "neutral"),
            timesfm_preds.get(d, "neutral"),
            moirai_median.get(d, "neutral"),
        ]
        if chronos_pipe and timesfm_model and moirai_predictor:
            if d not in chronos_preds or d not in timesfm_preds or d not in moirai_median:
                continue

        arm_pairs["train_majority_baseline"].append((maj_train, act))
        maj_vote = _vote_majority(c_preds)
        arm_pairs["tsfm_majority_vote_2of3"].append((maj_vote, act))
        unan = _vote_unanimous(c_preds)
        if unan is not None:
            arm_pairs["tsfm_unanimous_3of3"].append((unan, act))
        if d in moirai_band:
            arm_pairs["moirai_quantile_band_agree"].append((moirai_band[d], act))
        mom20 = _mom_pred(closes, i, 20, neutral_bps)
        hybrid = _vote_majority(c_preds + [mom20])
        arm_pairs["hybrid_mom20d_plus_tsfm_majority"].append((hybrid, act))
        guarded = maj_vote
        bull_ct = sum(1 for p in c_preds if p == "bull")
        if maj_vote == "bull" and bull_ct >= 3:
            guarded = maj_train
        arm_pairs["anti_bull_bias_guard_stack"].append((guarded, act))

    return arm_pairs


def main(argv: list[str] | None = None) -> int:
    _env_bootstrap()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--kospi-csv", type=Path, default=DEFAULT_KOSPI)
    ap.add_argument("--eval-days", type=int, default=252)
    ap.add_argument("--n-folds", type=int, default=5)
    ap.add_argument("--neutral-bps", type=float, default=5.0)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--pointer-out", type=Path, default=DEFAULT_POINTER)
    ap.add_argument("--run-stack-inference", action="store_true")
    ap.add_argument("--chronos-model", default="amazon/chronos-2")
    ap.add_argument("--chronos-device", default="cpu")
    ap.add_argument("--chronos-context", type=int, default=256)
    ap.add_argument("--timesfm-model", default="google/timesfm-2.5-200m-pytorch")
    ap.add_argument("--timesfm-context", type=int, default=256)
    ap.add_argument("--moirai-model", default="Salesforce/moirai-2.0-R-small")
    ap.add_argument("--moirai-context", type=int, default=256)
    ap.add_argument("--moirai-batch-size", type=int, default=16)
    ap.add_argument("--moirai-device", default="cpu")
    args = ap.parse_args(argv)

    if not args.kospi_csv.is_file():
        print(f"missing kospi csv: {args.kospi_csv}", file=sys.stderr)
        return 2

    series = _load_closes(args.kospi_csv)
    if len(series) < 30:
        print("insufficient kospi rows", file=sys.stderr)
        return 2
    if args.eval_days > 0:
        series = series[-args.eval_days :]
    dates = [d for d, _ in series]
    closes = [c for _, c in series]
    date_to_idx = {d: i for i, d in enumerate(dates)}
    folds = _blocked_folds(dates, args.n_folds)
    if not folds:
        print("no wf folds", file=sys.stderr)
        return 2

    probes = {
        "chronos2": _chronos2_probe(
            run_inference=args.run_stack_inference,
            model_id=args.chronos_model,
            device=args.chronos_device,
        ),
        "timesfm25": _timesfm_probe(run_inference=args.run_stack_inference, model_id=args.timesfm_model),
        "moirai2": _moirai_probe(run_inference=args.run_stack_inference, model_id=args.moirai_model),
    }

    chronos_pipe = timesfm_model = moirai_predictor = None
    if args.run_stack_inference:
        if probes["chronos2"].get("status") == "dependency_ok":
            chronos_pipe, load_meta = _load_chronos2_pipeline(args.chronos_model, args.chronos_device)
            probes["chronos2"] = {**probes["chronos2"], **load_meta}
        if probes["timesfm25"].get("status") == "dependency_ok":
            timesfm_model, load_meta = _load_timesfm_model(
                args.timesfm_model, max_context=args.timesfm_context, max_horizon=1
            )
            probes["timesfm25"] = {**probes["timesfm25"], **load_meta}
        if probes["moirai2"].get("status") == "dependency_ok":
            moirai_predictor, load_meta = _load_moirai2_predictor(
                args.moirai_model,
                context_length=args.moirai_context,
                prediction_length=1,
                batch_size=args.moirai_batch_size,
                device=args.moirai_device,
            )
            probes["moirai2"] = {**probes["moirai2"], **load_meta}

    arm_fold_rows: dict[str, list[dict[str, Any]]] = {
        "train_majority_baseline": [],
        "tsfm_majority_vote_2of3": [],
        "tsfm_unanimous_3of3": [],
        "moirai_quantile_band_agree": [],
        "hybrid_mom20d_plus_tsfm_majority": [],
        "anti_bull_bias_guard_stack": [],
    }

    for fi, (train, test) in enumerate(folds):
        if not args.run_stack_inference or not (chronos_pipe and timesfm_model and moirai_predictor):
            for arm_id in arm_fold_rows:
                arm_fold_rows[arm_id].append(
                    {
                        "fold": fi,
                        "test_dates": [test[0], test[-1]],
                        "directional_hit_rate": None,
                        "n_evaluated": 0,
                        "note": "pass --run-stack-inference with all deps loaded",
                    }
                )
            continue

        pairs_by_arm = _collect_fold_rows(
            closes=closes,
            dates=dates,
            date_to_idx=date_to_idx,
            train=train,
            test=test,
            neutral_bps=args.neutral_bps,
            chronos_pipe=chronos_pipe,
            timesfm_model=timesfm_model,
            moirai_predictor=moirai_predictor,
            chronos_context=args.chronos_context,
            timesfm_context=args.timesfm_context,
            moirai_context=args.moirai_context,
            moirai_batch=args.moirai_batch_size,
        )
        for arm_id, pairs in pairs_by_arm.items():
            m = _hit_from_pairs(pairs)
            arm_fold_rows[arm_id].append(
                {"fold": fi, "test_dates": [test[0], test[-1]], **m}
            )

    arms_out = [
        {
            "arm_id": arm_id,
            "model": "tsfm_stack_ensemble",
            "protocol": "blocked_walkforward_test_only",
            **_aggregate(arm_fold_rows[arm_id]),
        }
        for arm_id in arm_fold_rows
    ]

    wf = _load_json(DEFAULT_WF)
    wf_arms = ((wf or {}).get("blocked_walkforward_test_only") or {}).get("arms") or []
    majority_hr = next(
        (a.get("pooled_test_directional_hit_rate") for a in wf_arms if a.get("arm_id") == "majority_from_train"),
        None,
    )
    rq025 = _load_json(DEFAULT_RQ025)
    moirai_solo = next(
        (a.get("pooled_test_hr") for a in (rq025 or {}).get("arms") or [] if a.get("arm_id") == "moirai2_quantile_shadow"),
        None,
    )
    def _arm_bull_share(arm: dict[str, Any]) -> float | None:
        folds_list = arm.get("folds") or []
        nb = sum(int((f.get("pred_distribution") or {}).get("bull", 0)) for f in folds_list)
        nn = sum(int(f.get("n_evaluated") or 0) for f in folds_list)
        return round(nb / nn, 4) if nn else None

    def _is_straw_man(arm: dict[str, Any]) -> bool:
        bs = _arm_bull_share(arm)
        return bs is not None and bs >= 0.9

    honest_arms = [a for a in arms_out if not _is_straw_man(a) and a.get("pooled_test_directional_hit_rate") is not None]
    best_honest = max(honest_arms, key=lambda a: float(a["pooled_test_directional_hit_rate"])) if honest_arms else None
    best = max(arms_out, key=lambda a: (a.get("pooled_test_directional_hit_rate") or -1.0))

    out: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "rq_id": "RQ-026",
        "track_a_mutated": False,
        "prior_rq": "RQ-025",
        "purpose_ko": "3 TSFM 단일 암 초과 없음 → 스택 앙상블·quantile band·bull-bias guard",
        "window": {
            "eval_days": args.eval_days,
            "date_from": dates[0],
            "date_to": dates[-1],
            "neutral_bps": args.neutral_bps,
            "n_folds": args.n_folds,
        },
        "model_probes": probes,
        "blocked_walkforward_test_only": {"arms": arms_out},
        "compare": {
            "wf_majority_from_train_pooled_hr": majority_hr,
            "rq025_moirai2_solo_pooled_hr": moirai_solo,
        "best_arm_id": best.get("arm_id"),
        "best_pooled_hr": best.get("pooled_test_directional_hit_rate"),
        "best_honest_arm_id": best_honest.get("arm_id") if best_honest else None,
        "best_honest_pooled_hr": best_honest.get("pooled_test_directional_hit_rate") if best_honest else None,
        "best_vs_majority_pp": (
            round(float(best["pooled_test_directional_hit_rate"]) - float(majority_hr), 2)
            if best.get("pooled_test_directional_hit_rate") is not None and majority_hr is not None
            else None
        ),
        "best_honest_vs_majority_pp": (
            round(float(best_honest["pooled_test_directional_hit_rate"]) - float(majority_hr), 2)
            if best_honest and best_honest.get("pooled_test_directional_hit_rate") is not None and majority_hr is not None
            else None
        ),
        },
        "readout_ko": [],
        "reproduce": [
            "set TRANSFORMERS_NO_TF=1&& set USE_TF=0",
            "py scripts/run_rq026_kospi_tsfm_stack_ensemble_wf_shadow_v1.py --eval-days 252 --n-folds 5 --run-stack-inference",
        ],
        "do_not": [
            "Track A headline KPI 자동 교체",
            "combined_all_passed 자동 true",
            "live trading ON",
        ],
    }

    for arm in arms_out:
        hr = arm.get("pooled_test_directional_hit_rate")
        bull = None
        folds_list = arm.get("folds") or []
        if folds_list:
            nb = sum(int((f.get("pred_distribution") or {}).get("bull", 0)) for f in folds_list)
            nn = sum(int(f.get("n_evaluated") or 0) for f in folds_list)
            bull = round(nb / nn, 4) if nn else None
        vs_maj = (
            round(float(hr) - float(majority_hr), 2)
            if hr is not None and majority_hr is not None
            else None
        )
        straw = bull is not None and bull >= 0.9
        out["readout_ko"].append(
            f"{arm['arm_id']}: pooled {hr} (vs majority {vs_maj}pp, pred_bull_share={bull}"
            + ("; straw-man guard" if straw else "")
            + ")"
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output}")

    ref = best_honest or best
    pointer = {
        "schema": "rq026_tsfm_stack_research_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "rq_id": "RQ-026",
        "evidence": str(args.output.relative_to(ROOT)).replace("\\", "/"),
        "best_arm_id": ref.get("arm_id"),
        "best_pooled_hr": ref.get("pooled_test_directional_hit_rate"),
        "best_raw_arm_id": best.get("arm_id"),
        "best_raw_pooled_hr": best.get("pooled_test_directional_hit_rate"),
        "best_raw_straw_man": _is_straw_man(best),
        "wf_majority_beat_target": majority_hr,
        "beats_majority": (
            ref.get("pooled_test_directional_hit_rate") is not None
            and majority_hr is not None
            and float(ref["pooled_test_directional_hit_rate"]) > float(majority_hr)
            and not _is_straw_man(ref)
        ),
        "track_a_auto_merge": False,
    }
    args.pointer_out.parent.mkdir(parents=True, exist_ok=True)
    args.pointer_out.write_text(json.dumps(pointer, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.pointer_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
