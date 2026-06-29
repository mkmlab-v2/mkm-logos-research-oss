#!/usr/bin/env python3
"""Phase-3 shadow supplement: myeongni+sasang Sharpe lane + fABBA delta vs Arm A [HYPO].

Runs on the 180d science-core KOSPI panel (same cohort as shadow ablation v2).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.logos_shadow_eval_lib import load_kospi_yf_rows  # noqa: E402
from scripts.prophecy_fabba_sidecar_lib_v1 import (  # noqa: E402
    fabba_dependency_probe,
    resolve_backend,
    run_blocked_wf_arms_for_panel,
)
from scripts.run_prophecy_lens_profile_shadow_ablation_v1 import (  # noqa: E402
    DEFAULT_SCORE,
    DEFAULT_SCIENCE_JSONL,
    DEFAULT_SIDECAR,
    _extract_science_maps,
    _metrics_summary,
    _read_json,
    _run_backtest_slice,
    _utc_now,
)
from scripts.run_prophecy_lens_profile_shadow_ablation_v2 import (  # noqa: E402
    _relabel_rows_neutral,
    _walkforward_arm_summary,
)

DEFAULT_KOSPI_CSV = ROOT / "research/market_data/kospi_daily_external_yf.csv"
DEFAULT_BTC_CSV = ROOT / "research/market_data/btc_daily_external_yf.csv"
DEFAULT_V2 = ROOT / "reports/prophecy_lens_profile_shadow_ablation_v2_latest.json"
DEFAULT_RQ025 = ROOT / "reports/rq025_tsfm_delta_arms_v1_latest.json"
DEFAULT_WF_COMPARE = ROOT / "reports/kospi_prophecy_wf_holdout_compare_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/prophecy_lens_profile_shadow_ablation_phase3_v1_latest.json"
ART_OUT = ROOT / "docs/final/artifacts/prophecy_lens_profile_shadow_ablation_phase3_v1_latest.json"
SCHEMA = "prophecy_lens_profile_shadow_ablation_phase3_v1"


def _read_json_optional(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    return doc if isinstance(doc, dict) else {}


def _load_panel_rows(
    score_json: Path,
    *,
    target: str,
    neutral_bps: float,
) -> list[dict[str, Any]]:
    score_doc = _read_json(score_json)
    rows = score_doc.get("rows") or []
    filtered = [
        r
        for r in rows
        if isinstance(r, dict) and str(r.get("instrument") or "").strip().lower() == target
    ]
    filtered.sort(key=lambda x: str(x.get("eval_date") or ""))
    return _relabel_rows_neutral(filtered, neutral_bps)


def _kospi_closes_series(kospi_csv: Path) -> tuple[list[str], list[float]]:
    rows = load_kospi_yf_rows(kospi_csv)
    dates = [str(r["date"])[:10] for r in rows]
    closes = [float(r["close"]) for r in rows]
    return dates, closes


def _fabba_kospi_wf(
    *,
    kospi_csv: Path,
    eval_dates: list[str],
    n_folds: int,
    neutral_bps: float,
    lookback: int,
    ngram_size: int,
    tol: float,
    alpha: float,
    backend: str,
) -> dict[str, Any]:
    dates, closes = _kospi_closes_series(kospi_csv)
    resolved, backend_meta = resolve_backend(backend)
    panel = run_blocked_wf_arms_for_panel(
        instrument_id="kospi",
        dates=dates,
        closes=closes,
        eval_dates=eval_dates,
        n_folds=n_folds,
        neutral_bps=neutral_bps,
        lookback=lookback,
        ngram_size=ngram_size,
        tol=tol,
        backend=resolved,
        alpha=alpha,
    )
    panel["backend_meta"] = backend_meta
    panel["backend_resolved"] = resolved
    return panel


def _rq025_pointers(rq025: dict[str, Any], wf_compare: dict[str, Any]) -> dict[str, Any]:
    blocked = wf_compare.get("blocked_walkforward_test_only") or {}
    arms = blocked.get("arms") or []
    ensemble = next((a for a in arms if a.get("arm_id") == "per_date_kospi_ensemble"), {})
    majority = next((a for a in arms if a.get("arm_id") == "train_majority_straw_man"), {})
    moirai = None
    for arm in rq025.get("arms") or []:
        if arm.get("arm_id") == "moirai2_kospi_quantile_shadow":
            moirai = arm
            break
    return {
        "protocol_note": "RQ-025 / wf_compare = 252d/5bps KOSPI-only — delta is indicative not apples-to-apples",
        "per_date_kospi_ensemble_pooled_hr_252d_5bps": ensemble.get("pooled_test_directional_hit_rate"),
        "train_majority_pooled_hr_252d_5bps": majority.get("pooled_test_directional_hit_rate"),
        "moirai2_pooled_hr_252d_5bps": (moirai or {}).get("pooled_test_hr"),
        "rq025_registry": str(DEFAULT_RQ025),
        "wf_compare": str(DEFAULT_WF_COMPARE),
    }


def build_phase3(
    *,
    score_json: Path,
    sidecar_json: Path,
    science_jsonl: Path,
    kospi_csv: Path,
    v2_artifact: Path,
    fee_bps: float,
    neutral_bps: float,
    deadzone: float,
    logos_min_confidence: float,
    annual_trading_days: int,
    n_folds: int,
    wf_min_train_rows: int,
    wf_test_window_rows: int,
    fabba_lookback: int,
    fabba_ngram: int,
    fabba_tol: float,
    fabba_alpha: float,
    fabba_backend: str,
) -> dict[str, Any]:
    rows = _load_panel_rows(score_json, target="kospi", neutral_bps=neutral_bps)
    if not rows:
        raise SystemExit("empty kospi panel")

    science_sign_map, science_score_map = _extract_science_maps(science_jsonl)
    sidecar_doc = _read_json(sidecar_json)
    fee_rate = fee_bps / 10000.0

    omit = _run_backtest_slice(
        rows=rows,
        sidecar_doc=sidecar_doc,
        science_sign_map=science_sign_map,
        science_score_map=science_score_map,
        btc_prior={},
        logos_vote_mode="omit",
        logos_min_confidence=logos_min_confidence,
        fee_rate=fee_rate,
        deadzone=deadzone,
        annual_trading_days=annual_trading_days,
    )

    lens_ids = (
        "science+sasang",
        "myeongni+sasang",
        "sasang",
        "myeongni",
        "science+myeongni",
    )
    lens_arms = {lid: _metrics_summary(omit[lid]) for lid in lens_ids if lid in omit}

    my_sa = omit.get("myeongni+sasang") or {}
    arm_a = omit.get("science+sasang") or {}
    my_sa_m = my_sa.get("metrics") or {}
    arm_a_m = arm_a.get("metrics") or {}

    def _sim_lens(strategy_id: str):
        def _fn(test_rows: list[dict[str, Any]]) -> dict[str, Any]:
            return _run_backtest_slice(
                rows=test_rows,
                sidecar_doc=sidecar_doc,
                science_sign_map=science_sign_map,
                science_score_map=science_score_map,
                btc_prior={},
                logos_vote_mode="omit",
                logos_min_confidence=logos_min_confidence,
                fee_rate=fee_rate,
                deadzone=deadzone,
                annual_trading_days=annual_trading_days,
            )[strategy_id]

        return _fn

    wf_my_sa = _walkforward_arm_summary(
        rows=rows,
        arm_sim_fn=_sim_lens("myeongni+sasang"),
        min_train_rows=wf_min_train_rows,
        test_window_rows=wf_test_window_rows,
    )
    wf_arm_a = _walkforward_arm_summary(
        rows=rows,
        arm_sim_fn=_sim_lens("science+sasang"),
        min_train_rows=wf_min_train_rows,
        test_window_rows=wf_test_window_rows,
    )

    eval_dates = [str(r.get("eval_date") or "")[:10] for r in rows]
    fabba_probe = fabba_dependency_probe()
    fabba_panel = _fabba_kospi_wf(
        kospi_csv=kospi_csv,
        eval_dates=eval_dates,
        n_folds=n_folds,
        neutral_bps=neutral_bps,
        lookback=fabba_lookback,
        ngram_size=fabba_ngram,
        tol=fabba_tol,
        alpha=fabba_alpha,
        backend=fabba_backend,
    )

    def _arm_hr(panel: dict[str, Any], arm_id: str) -> float | None:
        for a in panel.get("arms") or []:
            if a.get("arm_id") == arm_id:
                v = a.get("pooled_test_directional_hit_rate")
                return float(v) if isinstance(v, (int, float)) else None
        return None

    fabba_slope_hr = _arm_hr(fabba_panel, "fabba_sidecar_last_slope")
    fabba_ngram_hr = _arm_hr(fabba_panel, "fabba_sidecar_ngram_lut")
    mom_hr = _arm_hr(fabba_panel, "mom_20d_baseline")

    v2_doc = _read_json_optional(v2_artifact)
    v2_arm_a_hr = ((v2_doc.get("arms") or {}).get("A") or {}).get("metrics") or {}
    v2_a_hr = v2_arm_a_hr.get("directional_hit_rate_active")
    v2_wf_a = ((v2_doc.get("walkforward") or {}).get("A_science_sasang") or {}).get(
        "mean_test_directional_hit_rate_active"
    )

    sharpe_rank = sorted(
        lens_arms.items(),
        key=lambda x: float((x[1] or {}).get("sharpe") or -999.0),
        reverse=True,
    )

    return {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "send_gate": "HOLD",
        "track_a_blocked": True,
        "protocol": {
            "cohort": "science_core_panel_kospi_180d",
            "date_start": eval_dates[0],
            "date_end": eval_dates[-1],
            "n_panel_rows": len(rows),
            "fee_bps": fee_bps,
            "neutral_bps": neutral_bps,
            "fabba_n_folds": n_folds,
            "fabba_params": {
                "lookback": fabba_lookback,
                "ngram_size": fabba_ngram,
                "tol": fabba_tol,
                "alpha": fabba_alpha,
                "backend_requested": fabba_backend,
            },
        },
        "myeongni_sasang_lane": {
            "purpose_ko": "PersonaDiary/중기 레인 — prophecy vote 제외, Sharpe·MDD 위험조정 검증",
            "strategy_id": "myeongni+sasang",
            "metrics": lens_arms.get("myeongni+sasang"),
            "vs_arm_a_science_sasang": {
                "hit_rate_delta_pp": round(
                    (float(my_sa_m.get("directional_hit_rate_active") or 0) - float(arm_a_m.get("directional_hit_rate_active") or 0))
                    * 100.0,
                    4,
                ),
                "sharpe_delta": round(
                    float(my_sa_m.get("sharpe") or 0) - float(arm_a_m.get("sharpe") or 0),
                    6,
                ),
                "total_return_delta_pp": round(
                    (float(my_sa_m.get("total_return") or 0) - float(arm_a_m.get("total_return") or 0)) * 100.0,
                    4,
                ),
                "mdd_delta_pp": round(
                    (float(my_sa_m.get("mdd") or 0) - float(arm_a_m.get("mdd") or 0)) * 100.0,
                    4,
                ),
            },
            "walkforward_blocked": wf_my_sa,
            "persona_diary_lane_recommended": bool(
                float(my_sa_m.get("sharpe") or 0) >= float(arm_a_m.get("sharpe") or 0)
            ),
            "prophecy_vote_recommended": False,
        },
        "lens_sharpe_ranking": [{"strategy_id": k, **v} for k, v in sharpe_rank],
        "fabba_delta_arms": {
            "fabba_dependency_probe": fabba_probe,
            "kospi_panel_wf": fabba_panel,
            "pooled_test_hr": {
                "fabba_sidecar_last_slope": fabba_slope_hr,
                "fabba_sidecar_ngram_lut": fabba_ngram_hr,
                "mom_20d_baseline": mom_hr,
            },
            "delta_vs_arm_a_full_panel_hr_pp": round((fabba_slope_hr - float(v2_a_hr)) * 100.0, 4)
            if fabba_slope_hr is not None and v2_a_hr is not None
            else None,
            "delta_vs_arm_a_wf_mean_hr_pp": round((fabba_slope_hr - float(v2_wf_a)) * 100.0, 4)
            if fabba_slope_hr is not None and v2_wf_a is not None
            else None,
            "note_ko": "fABBA = symbolic sidecar shadow; apca_stub on Windows unless fABBA wheel installed",
        },
        "rq025_reference": _rq025_pointers(_read_json_optional(DEFAULT_RQ025), _read_json_optional(DEFAULT_WF_COMPARE)),
        "walkforward_compare": {
            "A_science_sasang": wf_arm_a,
            "myeongni_sasang": wf_my_sa,
        },
        "headline_ko": [
            f"myeongni+sasang Sharpe={my_sa_m.get('sharpe')} vs A={arm_a_m.get('sharpe')}",
            f"myeongni+sasang WF mean HR={wf_my_sa.get('mean_test_directional_hit_rate_active')}",
            f"fABBA slope pooled HR={fabba_slope_hr} (A panel HR={v2_a_hr})",
            f"PersonaDiary lane={'yes' if float(my_sa_m.get('sharpe') or 0) >= float(arm_a_m.get('sharpe') or 0) else 'marginal'}",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--sidecar-json", type=Path, default=DEFAULT_SIDECAR)
    ap.add_argument("--science-jsonl", type=Path, default=DEFAULT_SCIENCE_JSONL)
    ap.add_argument("--kospi-csv", type=Path, default=DEFAULT_KOSPI_CSV)
    ap.add_argument("--v2-artifact", type=Path, default=DEFAULT_V2)
    ap.add_argument("--fee-bps", type=float, default=2.0)
    ap.add_argument("--neutral-bps", type=float, default=2.0)
    ap.add_argument("--coordinator-deadzone", type=float, default=0.001)
    ap.add_argument("--logos-min-confidence", type=float, default=0.25)
    ap.add_argument("--annual-trading-days", type=int, default=252)
    ap.add_argument("--n-folds", type=int, default=6)
    ap.add_argument("--wf-min-train-rows", type=int, default=30)
    ap.add_argument("--wf-test-window-rows", type=int, default=25)
    ap.add_argument("--fabba-lookback", type=int, default=20)
    ap.add_argument("--fabba-ngram", type=int, default=2)
    ap.add_argument("--fabba-tol", type=float, default=0.03)
    ap.add_argument("--fabba-alpha", type=float, default=0.1)
    ap.add_argument("--fabba-backend", choices=("auto", "apca_stub", "fabba"), default="auto")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--artifact-output", type=Path, default=ART_OUT)
    args = ap.parse_args(argv)

    payload = build_phase3(
        score_json=args.score_json,
        sidecar_json=args.sidecar_json,
        science_jsonl=args.science_jsonl,
        kospi_csv=args.kospi_csv,
        v2_artifact=args.v2_artifact,
        fee_bps=float(args.fee_bps),
        neutral_bps=float(args.neutral_bps),
        deadzone=abs(float(args.coordinator_deadzone)),
        logos_min_confidence=float(args.logos_min_confidence),
        annual_trading_days=max(1, int(args.annual_trading_days)),
        n_folds=max(2, int(args.n_folds)),
        wf_min_train_rows=max(2, int(args.wf_min_train_rows)),
        wf_test_window_rows=max(2, int(args.wf_test_window_rows)),
        fabba_lookback=int(args.fabba_lookback),
        fabba_ngram=int(args.fabba_ngram),
        fabba_tol=float(args.fabba_tol),
        fabba_alpha=float(args.fabba_alpha),
        fabba_backend=str(args.fabba_backend),
    )

    for path in (args.output, args.artifact_output):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    my = payload["myeongni_sasang_lane"]["metrics"]
    print(
        f"OK phase3 myeongni+sasang sharpe={my.get('sharpe')} "
        f"fabba_hr={payload['fabba_delta_arms']['pooled_test_hr'].get('fabba_sidecar_last_slope')} "
        f"-> {args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
