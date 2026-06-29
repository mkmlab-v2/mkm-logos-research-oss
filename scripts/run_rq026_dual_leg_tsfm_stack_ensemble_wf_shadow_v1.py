#!/usr/bin/env python3
"""[HYPO] RQ-026 TSFM stack ensemble dual-leg intersection WF (180d / 2bps).

Blocked walk-forward on KOSPI+BTC calendar intersection; pools stack arms across legs.
Compares to Primary recommended chain, Moirai dual-leg, fABBA sidecar — no Track A merge.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.prophecy_fabba_sidecar_lib_v1 import (  # noqa: E402
    load_dual_leg_intersection_window,
    pool_arms_across_instruments,
)
from scripts.run_rq025_chronos2_kospi_daily_wf_shadow_v1 import (  # noqa: E402
    _blocked_folds,
    _chronos2_probe,
    _load_chronos2_pipeline,
)
from scripts.run_rq025_moirai2_kospi_daily_wf_shadow_v1 import (  # noqa: E402
    _load_moirai2_predictor,
    _moirai_probe,
)
from scripts.run_rq025_timesfm25_kospi_daily_wf_shadow_v1 import (  # noqa: E402
    _load_timesfm_model,
    _timesfm_probe,
)
from scripts.run_rq026_kospi_tsfm_stack_ensemble_wf_shadow_v1 import (  # noqa: E402
    _aggregate,
    _collect_fold_rows,
    _hit_from_pairs,
)

DEFAULT_KOSPI = ROOT / "research/market_data/kospi_daily_external_yf.csv"
DEFAULT_BTC = ROOT / "research/market_data/btc_daily_external_yf.csv"
DEFAULT_OUT = ROOT / "reports/rq026_dual_leg_tsfm_stack_ensemble_wf_shadow_v1_latest.json"
DEFAULT_PRIMARY = ROOT / "reports/prophecy_hit_rate_eval_recommended_chain_run_latest.json"
DEFAULT_MOIRAI_DUAL = ROOT / "reports/rq025_moirai2_dual_leg_wf_shadow_v1_latest.json"
DEFAULT_FABBA_DUAL = ROOT / "reports/prophecy_fabba_sidecar_dual_leg_wf_v1_latest.json"
DEFAULT_KOSPI_STACK = ROOT / "reports/rq026_kospi_tsfm_stack_ensemble_wf_shadow_v1_latest.json"
SCHEMA = "rq026_dual_leg_tsfm_stack_ensemble_wf_shadow_v1"

ARM_IDS = (
    "train_majority_baseline",
    "tsfm_majority_vote_2of3",
    "tsfm_unanimous_3of3",
    "moirai_quantile_band_agree",
    "hybrid_mom20d_plus_tsfm_majority",
    "anti_bull_bias_guard_stack",
)


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


def _arm_bull_share(arm: dict[str, Any]) -> float | None:
    folds_list = arm.get("folds") or []
    if folds_list:
        nb = sum(int((f.get("pred_distribution") or {}).get("bull", 0)) for f in folds_list)
        nn = sum(int(f.get("n_evaluated") or 0) for f in folds_list)
        return round(nb / nn, 4) if nn else None
    dist = arm.get("pred_distribution") or {}
    n = int(arm.get("total_n_evaluated") or 0)
    bull = int(dist.get("bull") or 0)
    return round(bull / n, 4) if n else None


def _is_straw_man(arm: dict[str, Any]) -> bool:
    bs = _arm_bull_share(arm)
    return bs is not None and bs >= 0.9


def _pooled_arm_honest(pooled_arm: dict[str, Any], per_inst: list[dict[str, Any]]) -> bool:
    aid = pooled_arm.get("arm_id")
    if aid == "train_majority_baseline":
        return False
    if pooled_arm.get("pooled_test_directional_hit_rate") is None:
        return False
    for inst in per_inst:
        for arm in inst.get("arms") or []:
            if arm.get("arm_id") == aid and _is_straw_man(arm):
                return False
    return True


def _run_instrument_stack_panel(
    *,
    instrument_id: str,
    dates: list[str],
    closes: list[float],
    eval_dates: list[str],
    n_folds: int,
    neutral_bps: float,
    chronos_pipe: Any | None,
    timesfm_model: Any | None,
    moirai_predictor: Any | None,
    chronos_context: int,
    timesfm_context: int,
    moirai_context: int,
    moirai_batch: int,
    run_inference: bool,
) -> dict[str, Any]:
    date_to_idx = {d: i for i, d in enumerate(dates)}
    eval_set = [d for d in eval_dates if d in date_to_idx]
    folds = _blocked_folds(eval_set, n_folds)

    arm_fold_rows: dict[str, list[dict[str, Any]]] = {aid: [] for aid in ARM_IDS}
    models_ready = bool(chronos_pipe and timesfm_model and moirai_predictor)

    for fi, (train, test) in enumerate(folds):
        if not run_inference or not models_ready:
            for arm_id in ARM_IDS:
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
            neutral_bps=neutral_bps,
            chronos_pipe=chronos_pipe,
            timesfm_model=timesfm_model,
            moirai_predictor=moirai_predictor,
            chronos_context=chronos_context,
            timesfm_context=timesfm_context,
            moirai_context=moirai_context,
            moirai_batch=moirai_batch,
        )
        for arm_id, pairs in pairs_by_arm.items():
            m = _hit_from_pairs(pairs)
            arm_fold_rows[arm_id].append(
                {"fold": fi, "test_dates": [test[0], test[-1]], **m}
            )

    arms = [
        {
            "arm_id": arm_id,
            "model": "tsfm_stack_ensemble",
            "protocol": "blocked_walkforward_test_only",
            **_aggregate(arm_fold_rows[arm_id]),
            "folds": arm_fold_rows[arm_id],
        }
        for arm_id in ARM_IDS
    ]
    return {"instrument_id": instrument_id, "status": "ok", "arms": arms}


def main(argv: list[str] | None = None) -> int:
    _env_bootstrap()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--kospi-csv", type=Path, default=DEFAULT_KOSPI)
    ap.add_argument("--btc-csv", type=Path, default=DEFAULT_BTC)
    ap.add_argument("--last-n-intersection", type=int, default=180)
    ap.add_argument("--n-folds", type=int, default=6)
    ap.add_argument("--neutral-bps", type=float, default=2.0)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
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

    window = load_dual_leg_intersection_window(
        args.kospi_csv,
        args.btc_csv,
        last_n_intersection=args.last_n_intersection,
    )
    if window.get("status") != "ok":
        print(f"dual-leg window failed: {window}", file=sys.stderr)
        return 2

    eval_dates = window["intersection_dates"]
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

    per_inst = []
    for inst_id in ("kospi", "btc"):
        panel = window["panels"][inst_id]
        per_inst.append(
            _run_instrument_stack_panel(
                instrument_id=inst_id,
                dates=panel["dates"],
                closes=panel["closes"],
                eval_dates=eval_dates,
                n_folds=args.n_folds,
                neutral_bps=args.neutral_bps,
                chronos_pipe=chronos_pipe,
                timesfm_model=timesfm_model,
                moirai_predictor=moirai_predictor,
                chronos_context=args.chronos_context,
                timesfm_context=args.timesfm_context,
                moirai_context=args.moirai_context,
                moirai_batch=args.moirai_batch_size,
                run_inference=args.run_stack_inference,
            )
        )

    pooled = pool_arms_across_instruments(per_inst)
    honest_pooled = [a for a in pooled if _pooled_arm_honest(a, per_inst)]
    best_honest = (
        max(honest_pooled, key=lambda a: float(a["pooled_test_directional_hit_rate"]))
        if honest_pooled
        else None
    )
    best_raw = max(pooled, key=lambda a: (a.get("pooled_test_directional_hit_rate") or -1.0))

    primary = _load_json(DEFAULT_PRIMARY) or {}
    primary_hr = (primary.get("metrics") or {}).get("price_directional_hit_rate")
    moirai_dual = _load_json(DEFAULT_MOIRAI_DUAL) or {}
    moirai_hr = (moirai_dual.get("compare") or {}).get("moirai_dual_leg_pooled_hr")
    fabba_dual = _load_json(DEFAULT_FABBA_DUAL) or {}
    fabba_ngram_hr = (fabba_dual.get("compare_primary_recommended_chain") or {}).get(
        "sidecar_ngram_pooled_hr"
    )
    kospi_stack = _load_json(DEFAULT_KOSPI_STACK) or {}
    kospi_stack_arms = ((kospi_stack.get("blocked_walkforward_test_only") or {}).get("arms") or [])
    kospi_hybrid_hr = next(
        (a.get("pooled_test_directional_hit_rate") for a in kospi_stack_arms if a.get("arm_id") == "hybrid_mom20d_plus_tsfm_majority"),
        None,
    )

    best_hr = best_honest.get("pooled_test_directional_hit_rate") if best_honest else None

    out: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "rq_id": "RQ-026",
        "track_a_mutated": False,
        "send_gate": "HOLD",
        "prior_rq": "RQ-025",
        "purpose_ko": "3 TSFM 스택 앙상블 dual-leg 180d/2bps — recommended chain 코호트 shadow",
        "protocol": {
            "panel": "dual_leg_kospi_btc_intersection",
            "last_n_intersection": args.last_n_intersection,
            "neutral_bps": args.neutral_bps,
            "n_folds": args.n_folds,
            "eval_date_from": window["eval_date_from"],
            "eval_date_to": window["eval_date_to"],
        },
        "model_probes": probes,
        "per_instrument": per_inst,
        "dual_leg_pooled_arms": pooled,
        "compare": {
            "primary_recommended_chain_hr": primary_hr,
            "primary_n_evaluated": (primary.get("metrics") or {}).get("n_evaluated"),
            "moirai_dual_leg_pooled_hr": moirai_hr,
            "fabba_ngram_dual_leg_hr": fabba_ngram_hr,
            "kospi_only_hybrid_mom20d_stack_hr_252d_5bps": kospi_hybrid_hr,
            "best_honest_arm_id": best_honest.get("arm_id") if best_honest else None,
            "best_honest_dual_leg_pooled_hr": best_hr,
            "best_raw_arm_id": best_raw.get("arm_id"),
            "best_raw_dual_leg_pooled_hr": best_raw.get("pooled_test_directional_hit_rate"),
            "best_honest_vs_primary_pp": round(float(best_hr) - float(primary_hr), 6)
            if best_hr is not None and primary_hr is not None
            else None,
            "best_honest_vs_moirai_dual_pp": round(float(best_hr) - float(moirai_hr), 6)
            if best_hr is not None and moirai_hr is not None
            else None,
        },
        "interpretation_ko": [
            "dual-leg 180d/2bps = recommended eval chain 코호트 정렬 shadow",
            "Chronos-2 + TimesFM 2.5 + Moirai-2 median → majority/unanimous/hybrid arms",
            "Track A·Primary score·fabba sidecar 자동 merge 금지",
        ],
        "reproduce": (
            "set TRANSFORMERS_NO_TF=1&& set USE_TF=0&& "
            f"py scripts/run_rq026_dual_leg_tsfm_stack_ensemble_wf_shadow_v1.py "
            f"--last-n-intersection {args.last_n_intersection} --n-folds {args.n_folds} "
            f"--neutral-bps {args.neutral_bps} --run-stack-inference"
        ),
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    loaded = sum(1 for p in probes.values() if p.get("status") == "loaded")
    print(
        f"WROTE: {args.output} models_loaded={loaded}/3 "
        f"best_honest={best_honest.get('arm_id') if best_honest else None} "
        f"pooled={best_hr} vs_primary={out['compare'].get('best_honest_vs_primary_pp')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
