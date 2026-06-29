#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""[MAX_HYPO] Fully isolated max-theory offline sandbox — internal modules combined; Track A wall.

Orchestrates:
  1) ~1y OHLCV static LUT (dual-leg intersection cache)
  2) 3-lens equal-weight + shock/momentum overlay open (v2 multilens backtest)
  3) Per-date combo walk-forward with source signal + expanded prior (LUT-accelerated)
  4) Neutral-band sweep grid
  5) Shock-day audit (incl. 2026-06-08 / 2026-06-09 spotlight)
  6) Bull-abstain / shock-continuation overlay ablation on multilens baseline
  7) Shock rebound guard grid + overnight gap open trigger ablation
  8) Intraday shock proxy (open composite + open→low oracle ceiling)
  9) Causal open-only limit ladder + blocked walk-forward on composite overlay
  10) Vol regime + prior-range-low open proxies + conservative composite WF
  11) Range-or-composite ensemble + range-threshold holdout / blocked WF
  12) T8 triple causal proxy (range∨composite∨vol-gated) + holdout fold day audit
  13) Range rebound-guard refinement (guard sweep + overnight gap-up skip) + summary MD
  14) Prior-mild AND range-low conjunction vs range-only (fold1 regression fix)
  15) T10/T11 ensemble (T9 AND range leg ∨ composite) vs T7/T8 + holdout
  16) T12 soft range-cap uplift recovery (mild∧range ∨ soft range-only ∨ composite)
  17) T13 composite overnight mild-gate vs T10
  18) Recommended sandbox tier manifest (T10/T13 + evidence pointers)

NEVER writes operational ``docs/final/artifacts/*_latest`` score/eval paths.
FAIL-COMP-004: B→A·실매매 자동 합선 없음.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SANDBOX_ROOT = ROOT / "experiments" / "max_hypo_unbound"
DEFAULT_RECIPE = SANDBOX_ROOT / "max_hypo_recipe_v1.json"
DEFAULT_LUT = SANDBOX_ROOT / "cache" / "ohlcv_lut_252d_v1.json"
DEFAULT_OUT = SANDBOX_ROOT / "results" / "max_theory_unbound_simulation_v1_latest.json"
DEFAULT_SCORE = SANDBOX_ROOT / "cache" / "kospi_score_252d_v1.json"
DEFAULT_SCORE_FALLBACK = ROOT / "docs/final/artifacts/btrack_prophecy_score_kospi_only_latest.json"
DEFAULT_PANEL = ROOT / "reports/btrack_session_myeongni_panel_252d_v1.csv"
KOSPI_CSV = ROOT / "research/market_data/kospi_daily_external_yf.csv"
BTC_CSV = ROOT / "research/market_data/btc_daily_external_yf.csv"
EVOLUTION_RULES = ROOT / "data/commander/kospi_june2026_prophecy_evolution_v1.json"
FILLS_CACHE = ROOT / "reports/btrack_fills_daily_feature_cache_v1_latest.json"
SCHEMA = "max_theory_unbound_simulation_v1"
MAX_HYPO_LABEL = "[MAX_HYPO][SANDBOX]"

FORBIDDEN_OUTPUTS = frozenset(
    {
        "docs/final/artifacts/btrack_prophecy_score_latest.json",
        "docs/final/artifacts/prophecy_hit_rate_eval_latest.json",
        "docs/final/artifacts/btrack_hypothesis_prophecy_latest.json",
    }
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def assert_output_path_isolated(out_path: Path) -> None:
    """Hard wall: refuse writes that would collide with Track A operational SSOT."""
    rel = _rel(out_path.resolve())
    norm = rel.replace("\\", "/").lower()
    for forbidden in FORBIDDEN_OUTPUTS:
        if norm.endswith(forbidden.lower()) or norm == forbidden.lower():
            raise ValueError(f"MAX_HYPO wall: forbidden output path {rel}")
    if "docs/final/artifacts" in norm and out_path.name.endswith("_latest.json"):
        if "max_hypo" not in norm and "sandbox" not in norm:
            raise ValueError(
                f"MAX_HYPO wall: suspicious *_latest.json under docs/final/artifacts: {rel}"
            )


def load_recipe(path: Path) -> dict[str, Any]:
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    if doc.get("schema") != "max_hypo_recipe_v1":
        raise ValueError(f"expected max_hypo_recipe_v1, got {doc.get('schema')}")
    return doc


def max_hypo_lens_weights(recipe: dict[str, Any]) -> dict[str, float]:
    w = dict(recipe.get("lens_weights_v2_max") or {})
    keys = list(w.keys())
    total = sum(float(w.get(k, 0.0)) for k in keys)
    if total <= 0:
        raise ValueError("lens_weights_v2_max sum must be > 0")
    return {k: round(float(w.get(k, 0.0)) / total, 4) for k in keys}


def operational_baseline_catalog(recipe: dict[str, Any]) -> dict[str, dict[str, Any]]:
    from scripts.run_kospi_multilens_blend_backtest_v1 import _variant_catalog

    rules = json.loads(EVOLUTION_RULES.read_text(encoding="utf-8-sig"))
    cat = _variant_catalog(rules)
    baseline_id = "v2_lens3_heavy"
    if baseline_id not in cat:
        baseline_id = "v2_default" if "v2_default" in cat else next(iter(cat))
    return {
        "operational_baseline": cat[baseline_id],
    }


def max_hypo_catalog(recipe: dict[str, Any]) -> dict[str, dict[str, Any]]:
    from scripts.kospi_june2026_multilens_blend_v1 import default_weights_v2
    from scripts.run_kospi_multilens_blend_backtest_v1 import _normalize_weights

    v2_keys = list(default_weights_v2().keys())
    w = max_hypo_lens_weights(recipe)
    full = {k: 0.0 for k in v2_keys}
    for k, v in w.items():
        if k in full:
            full[k] = v
    shock = recipe.get("shock_overlay") if isinstance(recipe.get("shock_overlay"), dict) else {}
    min_w = float(shock.get("min_weight") or 0.2)
    if full.get("momentum_overlay", 0.0) < min_w:
        full["momentum_overlay"] = min_w
    return {
        "max_hypo_lens3_shock_open": {
            "profile": "v2_multilens",
            "weights": _normalize_weights(full, v2_keys),
            "note": "sasang+myeongni+macro+momentum equal; logos 0; shock channel open",
        }
    }


def _date_window_from_lut(lut_path: Path) -> tuple[str, str]:
    from scripts.btrack_ohlcv_feature_lut_lib_v1 import load_lut_document

    doc = load_lut_document(lut_path)
    dates = list(doc.get("intersection_dates") or [])
    if not dates:
        raise ValueError("LUT has no intersection_dates")
    return str(dates[0]), str(dates[-1])


def ensure_ohlcv_lut(
    *,
    recipe: dict[str, Any],
    kospi_csv: Path,
    btc_csv: Path,
    lut_path: Path,
    dry_run: bool,
) -> dict[str, Any]:
    fuel = recipe.get("input_fuel") if isinstance(recipe.get("input_fuel"), dict) else {}
    last_n = int(fuel.get("ohlcv_lut_last_n_intersection") or 252)
    if dry_run:
        return {
            "step": "ohlcv_lut",
            "skipped": True,
            "would_build": _rel(lut_path),
            "last_n_intersection": last_n,
        }
    from scripts.btrack_ohlcv_feature_lut_lib_v1 import build_lut_document

    doc = build_lut_document(
        kospi_csv=kospi_csv,
        btc_csv=btc_csv,
        generated_at_utc=_utc_now(),
        last_n_intersection=last_n if last_n > 0 else None,
    )
    lut_path.parent.mkdir(parents=True, exist_ok=True)
    lut_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "step": "ohlcv_lut",
        "path": _rel(lut_path),
        "n_intersection_dates": doc.get("stats", {}).get("n_intersection_dates"),
        "date_from": (doc.get("intersection_dates") or [None])[0],
        "date_to": (doc.get("intersection_dates") or [None])[-1],
    }


def run_multilens_arms(
    *,
    recipe: dict[str, Any],
    panel_csv: Path,
    kospi_csv: Path,
    date_from: str,
    date_to: str,
    dry_run: bool,
) -> dict[str, Any]:
    if dry_run:
        return {
            "step": "multilens_backtest",
            "skipped": True,
            "variants": ["operational_baseline", "max_hypo_lens3_shock_open"],
            "window": {"from": date_from, "to": date_to},
        }
    from scripts.build_kospi_june2026_daily_prophecy_calendar_v1 import _read_json
    from scripts.run_kospi_multilens_blend_backtest_v1 import (
        EVOLUTION_RULES as RULES_PATH,
        _load_closes,
        _load_panel,
        run_backtest,
    )

    rules = _read_json(RULES_PATH)
    if not rules:
        raise RuntimeError("missing evolution rules")
    panel = _load_panel(panel_csv)
    closes = _load_closes(kospi_csv)
    catalog = {**operational_baseline_catalog(recipe), **max_hypo_catalog(recipe)}
    doc = run_backtest(
        panel_by_date=panel,
        closes=closes,
        date_from=date_from,
        date_to=date_to,
        rules=rules,
        catalog=catalog,
        four_ai_modes=("current",),
    )
    variants = []
    for v in doc.get("variants") or []:
        if not isinstance(v, dict):
            continue
        m = v.get("metrics") or {}
        variants.append(
            {
                "variant_id": v.get("variant_id"),
                "directional_hit_rate": m.get("directional_hit_rate"),
                "soft_hit_rate": m.get("soft_hit_rate"),
                "n_scored": m.get("n_scored"),
                "neutral_draw": m.get("neutral_draw"),
                "weights": v.get("weights"),
            }
        )
    max_row = next((x for x in variants if str(x.get("variant_id", "")).startswith("max_hypo")), {})
    base_row = next((x for x in variants if "baseline" in str(x.get("variant_id", ""))), {})
    delta = None
    if max_row.get("directional_hit_rate") is not None and base_row.get("directional_hit_rate") is not None:
        delta = round(float(max_row["directional_hit_rate"]) - float(base_row["directional_hit_rate"]), 4)
    return {
        "step": "multilens_backtest",
        "window": doc.get("window"),
        "variants": variants,
        "delta_max_hypo_minus_baseline_directional": delta,
    }


def run_neutral_band_sweep(
    *,
    recipe: dict[str, Any],
    panel_csv: Path,
    kospi_csv: Path,
    date_from: str,
    date_to: str,
    dry_run: bool,
) -> dict[str, Any]:
    sweep = list(recipe.get("decision_mode", {}).get("neutral_band_sweep") or [0.04, 0.06])
    if dry_run:
        return {"step": "neutral_band_sweep", "skipped": True, "grid": sweep}
    from scripts.build_kospi_june2026_daily_prophecy_calendar_v1 import _read_json
    from scripts.run_kospi_multilens_blend_backtest_v1 import (
        EVOLUTION_RULES as RULES_PATH,
        _load_closes,
        _load_panel,
        run_backtest,
    )

    rules_base = _read_json(RULES_PATH)
    panel = _load_panel(panel_csv)
    closes = _load_closes(kospi_csv)
    catalog = max_hypo_catalog(recipe)
    rows: list[dict[str, Any]] = []
    for nb in sweep:
        rules = deepcopy(rules_base)
        rules["neutral_band"] = float(nb)
        doc = run_backtest(
            panel_by_date=panel,
            closes=closes,
            date_from=date_from,
            date_to=date_to,
            rules=rules,
            catalog=catalog,
            four_ai_modes=("current",),
        )
        v0 = (doc.get("variants") or [{}])[0]
        m = v0.get("metrics") or {}
        rows.append(
            {
                "neutral_band": float(nb),
                "directional_hit_rate": m.get("directional_hit_rate"),
                "neutral_draw": m.get("neutral_draw"),
                "n_scored": m.get("n_scored"),
            }
        )
    best = max(rows, key=lambda r: float(r.get("directional_hit_rate") or -1)) if rows else {}
    return {"step": "neutral_band_sweep", "rows": rows, "best_by_directional": best}


def run_walkforward(
    *,
    recipe: dict[str, Any],
    score_json: Path,
    lut_path: Path,
    wf_out: Path,
    dry_run: bool,
) -> dict[str, Any]:
    wf = recipe.get("walkforward") if isinstance(recipe.get("walkforward"), dict) else {}
    n_folds = int(wf.get("n_folds") or 4)
    target = str(wf.get("target_instrument") or "kospi")
    if dry_run:
        return {"step": "walkforward", "skipped": True, "n_folds": n_folds, "target": target}
    cmd = [
        sys.executable,
        str(ROOT / "scripts/run_prophecy_per_date_combo_walkforward_v1.py"),
        "--score-json",
        str(score_json),
        "--kospi-csv",
        str(KOSPI_CSV),
        "--btc-csv",
        str(BTC_CSV),
        "--target-instrument",
        target,
        "--n-folds",
        str(n_folds),
        "--include-source-direction-signal",
        "--include-expanded-prior-features",
        "--ohlcv-lut-json",
        str(lut_path),
        "--output",
        str(wf_out),
    ]
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    summary: dict[str, Any] = {
        "step": "walkforward",
        "exit_code": proc.returncode,
        "output": _rel(wf_out),
        "cmd": " ".join(cmd),
    }
    if wf_out.is_file() and proc.returncode == 0:
        wf_doc = json.loads(wf_out.read_text(encoding="utf-8"))
        agg = wf_doc.get("aggregate") if isinstance(wf_doc.get("aggregate"), dict) else {}
        summary["mean_test_accuracy"] = agg.get("mean_test_accuracy", wf_doc.get("mean_test_accuracy"))
        summary["n_folds_effective"] = wf_doc.get("n_folds_effective")
        summary["n_distinct_eval_dates"] = wf_doc.get("inputs", {}).get("n_distinct_eval_dates")
        summary["n_walkforward_folds"] = wf_doc.get("inputs", {}).get("n_walkforward_folds")
        summary["feature_source"] = wf_doc.get("inputs", {}).get("feature_source")
    else:
        summary["stderr_tail"] = (proc.stderr or "")[-800:]
    return summary


def run_shock_overlay_ablation_sidecar(
    *,
    recipe: dict[str, Any],
    score_json: Path,
    kospi_csv: Path,
    spotlight_dates: list[str],
    out_path: Path,
    dry_run: bool,
) -> dict[str, Any]:
    """prior_day_shock_bear_abstain_v0 ablation on sandbox score panel (restoration spike family)."""
    ablation = recipe.get("shock_overlay_ablation") if isinstance(recipe.get("shock_overlay_ablation"), dict) else {}
    overlay = str(ablation.get("overlay") or "prior_day_shock_bear_abstain_v0")
    sweep = list(ablation.get("prior_return_threshold_sweep") or [-0.048, -0.06])
    recommended = float(ablation.get("prior_return_threshold_recommended") or -0.06)

    if dry_run:
        return {
            "step": "shock_overlay_ablation",
            "skipped": True,
            "overlay": overlay,
            "threshold_sweep": sweep,
            "output": _rel(out_path),
        }

    from scripts.run_prophecy_restoration_spike import (
        _apply_overlay,
        _eval_directional_hit,
        _load_json,
        _prior_completed_daily_return_by_eval_date,
    )

    if not score_json.is_file():
        return {
            "step": "shock_overlay_ablation",
            "skipped": True,
            "reason": f"missing score-json: {_rel(score_json)}",
        }
    if not kospi_csv.is_file():
        return {
            "step": "shock_overlay_ablation",
            "skipped": True,
            "reason": f"missing kospi-csv: {_rel(kospi_csv)}",
        }

    score_doc = _load_json(score_json)
    if not score_doc:
        return {"step": "shock_overlay_ablation", "skipped": True, "reason": "invalid score-json"}

    raw_rows = score_doc.get("rows")
    rows_in = [r for r in raw_rows if isinstance(r, dict)] if isinstance(raw_rows, list) else [score_doc]
    prior_map = _prior_completed_daily_return_by_eval_date(kospi_csv)
    base_rate, base_n, base_hits = _eval_directional_hit(rows_in)

    rows_by_date: dict[str, dict[str, Any]] = {}
    for r in rows_in:
        ed = str(r.get("eval_date") or "")[:10]
        if ed:
            rows_by_date[ed] = r

    sweep_rows: list[dict[str, Any]] = []
    best_delta: dict[str, Any] | None = None
    for thr in sweep:
        thr_f = float(thr)
        overlaid, n_mod = _apply_overlay(
            rows_in,
            overlay=overlay,
            stress_years=set(),
            prior_return_by_date=prior_map,
            prior_return_threshold=thr_f,
        )
        ov_rate, ov_n, ov_hits = _eval_directional_hit(overlaid)
        delta = round(float(ov_rate) - float(base_rate), 6) if ov_rate is not None and base_rate is not None else None
        row = {
            "prior_return_threshold": thr_f,
            "prior_return_threshold_pct": round(thr_f * 100.0, 4),
            "baseline_hit_rate": base_rate,
            "after_overlay_hit_rate": ov_rate,
            "delta_hit_rate": delta,
            "overlay_rows_modified": n_mod,
            "n_evaluated": ov_n,
        }
        sweep_rows.append(row)
        if delta is not None and (best_delta is None or delta > best_delta.get("delta_hit_rate", -999)):
            best_delta = row

    overlaid_rec, n_mod_rec = _apply_overlay(
        rows_in,
        overlay=overlay,
        stress_years=set(),
        prior_return_by_date=prior_map,
        prior_return_threshold=recommended,
    )
    ov_rate_rec, _, _ = _eval_directional_hit(overlaid_rec)
    overlaid_by_date = {str(r.get("eval_date") or "")[:10]: r for r in overlaid_rec}

    spotlight_rows: list[dict[str, Any]] = []
    for dk in spotlight_dates:
        base_r = rows_by_date.get(dk)
        ov_r = overlaid_by_date.get(dk)
        pr = prior_map.get(dk)
        if not base_r:
            spotlight_rows.append({"date": dk, "status": "missing_score_row"})
            continue
        base_pred = str(base_r.get("predicted_direction") or "").strip().lower()
        after_pred = str((ov_r or base_r).get("predicted_direction") or "").strip().lower()
        actual = str(base_r.get("actual_direction") or "").strip().lower()
        spotlight_rows.append(
            {
                "date": dk,
                "prior_completed_daily_return_pct": round(pr * 100.0, 4) if pr is not None else None,
                "baseline_predicted": base_pred,
                "after_overlay_predicted": after_pred,
                "actual_direction": actual,
                "overlay_modified": base_pred != after_pred,
                "baseline_hit": base_pred == actual if actual else None,
                "after_overlay_hit": after_pred == actual if actual else None,
            }
        )

    payload: dict[str, Any] = {
        "schema": "max_hypo_shock_overlay_ablation_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "hypothesis_tag": "[MAX_HYPO][HYPO]",
        "parent_spike_schema": "prophecy_overlay_ablation_spike_v1",
        "inputs": {
            "score_json": _rel(score_json),
            "kospi_csv": _rel(kospi_csv),
            "overlay": overlay,
            "prior_return_threshold_recommended": recommended,
        },
        "baseline": {
            "price_directional_hit_rate": base_rate,
            "n_evaluated": base_n,
            "hits": base_hits,
        },
        "recommended_threshold": {
            "prior_return_threshold": recommended,
            "after_overlay_hit_rate": ov_rate_rec,
            "delta_hit_rate": round(float(ov_rate_rec) - float(base_rate), 6)
            if ov_rate_rec is not None and base_rate is not None
            else None,
            "overlay_rows_modified": n_mod_rec,
        },
        "threshold_sweep": sweep_rows,
        "best_delta_in_sweep": best_delta,
        "spotlight": spotlight_rows,
        "interpretation_ko": {
            "6_8_bull_miss": (
                "overlay는 bear→neutral만 수정; baseline이 bull이면 6/8 급락일 방향 miss는 그대로일 수 있음"
            ),
            "6_9_prior_shock": (
                "6/9 전일(6/8) 수익률이 임계 이하이면 bear 예측만 neutral로 강등 — bull 예측은 유지"
            ),
        },
        "track_wall": "no_track_a_live_auto_merge",
    }

    assert_output_path_isolated(out_path.resolve())
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "step": "shock_overlay_ablation",
        "output": _rel(out_path),
        "overlay": overlay,
        "baseline_hit_rate": base_rate,
        "recommended_threshold": recommended,
        "recommended_delta_hit_rate": payload["recommended_threshold"].get("delta_hit_rate"),
        "best_sweep_delta_hit_rate": (best_delta or {}).get("delta_hit_rate"),
        "spotlight": spotlight_rows,
    }


def build_multilens_eval_rows(
    *,
    recipe: dict[str, Any],
    panel_csv: Path,
    kospi_csv: Path,
    date_from: str,
    date_to: str,
    variant_key: str = "operational_baseline",
    neutral_bps: float = 5.0,
) -> list[dict[str, Any]]:
    """Per-date multilens predictions + actuals for overlay ablation ([MAX_HYPO] sandbox)."""
    from scripts.build_kospi_june2026_daily_prophecy_calendar_v1 import _read_json
    from scripts.kospi_june2026_multilens_blend_v1 import load_ensemble_kospi_per_date, load_static_lenses
    from scripts.run_kospi_multilens_blend_backtest_v1 import (
        EVOLUTION_RULES as RULES_PATH,
        _direction_from_return,
        _load_closes,
        _load_panel,
        _predict_v2,
    )

    rules = _read_json(RULES_PATH)
    panel = _load_panel(panel_csv)
    closes = _load_closes(kospi_csv)
    catalog = operational_baseline_catalog(recipe)
    if variant_key not in catalog:
        raise KeyError(f"unknown multilens variant_key: {variant_key}")
    spec = catalog[variant_key]
    static_lenses = load_static_lenses()
    neutral_band = float(rules.get("neutral_band", 0.06))
    blend_policy = dict(rules.get("blend_policy_v2") or {})
    coord_policy = dict(rules.get("four_ai_coordinator_policy") or {})
    eval_dates = sorted(d for d in panel if date_from <= d <= date_to and d in closes)
    ensemble_by_date = load_ensemble_kospi_per_date(eval_dates)
    sorted_dates = sorted(closes.keys())
    rows_out: list[dict[str, Any]] = []
    for dk in eval_dates:
        idx = sorted_dates.index(dk)
        if idx < 1:
            continue
        prev = sorted_dates[idx - 1]
        prev_close = closes[prev]
        if not prev_close:
            continue
        act_ret = (closes[dk] - prev_close) / prev_close
        actual = _direction_from_return(act_ret, neutral_bps)
        pred, _meta = _predict_v2(
            dk,
            panel_row=panel[dk],
            closes=closes,
            static_lenses=static_lenses,
            ensemble_row=ensemble_by_date.get(dk),
            weights=spec["weights"],
            blend_policy=blend_policy,
            neutral_band=neutral_band,
            four_ai_mode="current",
            coord_policy=coord_policy,
        )
        rows_out.append(
            {
                "eval_date": dk,
                "predicted_direction": pred,
                "actual_direction": actual,
                "session_return_pct": round(act_ret * 100.0, 4),
            }
        )
    return rows_out


def _overlay_ablation_sweep(
    *,
    rows_in: list[dict[str, Any]],
    overlay: str,
    sweep: list[float],
    recommended: float,
    prior_map: dict[str, float],
    spotlight_dates: list[str],
) -> dict[str, Any]:
    from scripts.run_prophecy_restoration_spike import (
        _apply_overlay,
        _eval_directional_hit,
    )

    base_rate, base_n, base_hits = _eval_directional_hit(rows_in)
    rows_by_date = {str(r.get("eval_date") or "")[:10]: r for r in rows_in if r.get("eval_date")}

    sweep_rows: list[dict[str, Any]] = []
    best_delta: dict[str, Any] | None = None
    for thr in sweep:
        thr_f = float(thr)
        overlaid, n_mod = _apply_overlay(
            rows_in,
            overlay=overlay,
            stress_years=set(),
            prior_return_by_date=prior_map,
            prior_return_threshold=thr_f,
        )
        ov_rate, ov_n, _ = _eval_directional_hit(overlaid)
        delta = round(float(ov_rate) - float(base_rate), 6) if ov_rate is not None and base_rate is not None else None
        row = {
            "prior_return_threshold": thr_f,
            "prior_return_threshold_pct": round(thr_f * 100.0, 4),
            "baseline_hit_rate": base_rate,
            "after_overlay_hit_rate": ov_rate,
            "delta_hit_rate": delta,
            "overlay_rows_modified": n_mod,
            "n_evaluated": ov_n,
        }
        sweep_rows.append(row)
        if delta is not None and (best_delta is None or delta > best_delta.get("delta_hit_rate", -999)):
            best_delta = row

    overlaid_rec, n_mod_rec = _apply_overlay(
        rows_in,
        overlay=overlay,
        stress_years=set(),
        prior_return_by_date=prior_map,
        prior_return_threshold=recommended,
    )
    ov_rate_rec, _, _ = _eval_directional_hit(overlaid_rec)
    overlaid_by_date = {str(r.get("eval_date") or "")[:10]: r for r in overlaid_rec}

    spotlight_rows: list[dict[str, Any]] = []
    for dk in spotlight_dates:
        base_r = rows_by_date.get(dk)
        ov_r = overlaid_by_date.get(dk)
        pr = prior_map.get(dk)
        if not base_r:
            spotlight_rows.append({"date": dk, "status": "missing_eval_row"})
            continue
        base_pred = str(base_r.get("predicted_direction") or "").strip().lower()
        after_pred = str((ov_r or base_r).get("predicted_direction") or "").strip().lower()
        actual = str(base_r.get("actual_direction") or "").strip().lower()
        spotlight_rows.append(
            {
                "date": dk,
                "prior_completed_daily_return_pct": round(pr * 100.0, 4) if pr is not None else None,
                "baseline_predicted": base_pred,
                "after_overlay_predicted": after_pred,
                "actual_direction": actual,
                "overlay_modified": base_pred != after_pred,
                "baseline_hit": base_pred == actual if actual else None,
                "after_overlay_hit": after_pred == actual if actual else None,
            }
        )

    return {
        "overlay": overlay,
        "baseline": {
            "price_directional_hit_rate": base_rate,
            "n_evaluated": base_n,
            "hits": base_hits,
        },
        "recommended_threshold": {
            "prior_return_threshold": recommended,
            "after_overlay_hit_rate": ov_rate_rec,
            "delta_hit_rate": round(float(ov_rate_rec) - float(base_rate), 6)
            if ov_rate_rec is not None and base_rate is not None
            else None,
            "overlay_rows_modified": n_mod_rec,
        },
        "threshold_sweep": sweep_rows,
        "best_delta_in_sweep": best_delta,
        "spotlight": spotlight_rows,
    }


def run_bull_abstain_overlay_ablation_sidecar(
    *,
    recipe: dict[str, Any],
    panel_csv: Path,
    kospi_csv: Path,
    date_from: str,
    date_to: str,
    spotlight_dates: list[str],
    out_path: Path,
    dry_run: bool,
) -> dict[str, Any]:
    """Multilens operational baseline + prior-day shock bull overlays ([HYPO] V-rebound ablation)."""
    ablation = (
        recipe.get("bull_abstain_overlay_ablation")
        if isinstance(recipe.get("bull_abstain_overlay_ablation"), dict)
        else {}
    )
    overlays = list(
        ablation.get("overlays")
        or ["prior_day_shock_bull_abstain_v0", "prior_day_shock_bull_to_bear_v0"]
    )
    sweep = list(ablation.get("prior_return_threshold_sweep") or [-0.03, -0.048, -0.06, -0.08])
    recommended = float(ablation.get("prior_return_threshold_recommended") or -0.06)
    variant_key = str(ablation.get("multilens_variant") or "operational_baseline")

    if dry_run:
        return {
            "step": "bull_abstain_overlay_ablation",
            "skipped": True,
            "overlays": overlays,
            "threshold_sweep": sweep,
            "output": _rel(out_path),
        }

    if not panel_csv.is_file():
        return {
            "step": "bull_abstain_overlay_ablation",
            "skipped": True,
            "reason": f"missing panel-csv: {_rel(panel_csv)}",
        }
    if not kospi_csv.is_file():
        return {
            "step": "bull_abstain_overlay_ablation",
            "skipped": True,
            "reason": f"missing kospi-csv: {_rel(kospi_csv)}",
        }

    from scripts.run_prophecy_restoration_spike import _prior_completed_daily_return_by_eval_date

    rows_in = build_multilens_eval_rows(
        recipe=recipe,
        panel_csv=panel_csv,
        kospi_csv=kospi_csv,
        date_from=date_from,
        date_to=date_to,
        variant_key=variant_key,
    )
    if not rows_in:
        return {
            "step": "bull_abstain_overlay_ablation",
            "skipped": True,
            "reason": "no multilens eval rows in window",
        }

    prior_map = _prior_completed_daily_return_by_eval_date(kospi_csv)
    overlay_results: list[dict[str, Any]] = []
    for overlay in overlays:
        overlay_results.append(
            _overlay_ablation_sweep(
                rows_in=rows_in,
                overlay=str(overlay),
                sweep=sweep,
                recommended=recommended,
                prior_map=prior_map,
                spotlight_dates=spotlight_dates,
            )
        )

    best_overlay_row: dict[str, Any] | None = None
    for item in overlay_results:
        bd = item.get("best_delta_in_sweep") or {}
        delta = bd.get("delta_hit_rate")
        if delta is None:
            continue
        if best_overlay_row is None or delta > best_overlay_row.get("delta_hit_rate", -999):
            best_overlay_row = {
                "overlay": item.get("overlay"),
                **bd,
            }

    payload: dict[str, Any] = {
        "schema": "max_hypo_bull_abstain_overlay_ablation_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "hypothesis_tag": "[MAX_HYPO][HYPO]",
        "parent_spike_schema": "prophecy_overlay_ablation_spike_v1",
        "inputs": {
            "panel_csv": _rel(panel_csv),
            "kospi_csv": _rel(kospi_csv),
            "date_from": date_from,
            "date_to": date_to,
            "multilens_variant": variant_key,
            "overlays": overlays,
            "prior_return_threshold_recommended": recommended,
            "n_eval_rows": len(rows_in),
        },
        "multilens_baseline_hit_rate": overlay_results[0]["baseline"]["price_directional_hit_rate"]
        if overlay_results
        else None,
        "overlay_results": overlay_results,
        "best_overlay_in_sweep": best_overlay_row,
        "interpretation_ko": {
            "6_8_bull_miss": (
                "multilens baseline이 bull이면 prior-day shock bull→neutral/bear 오버레이로 "
                "6/8 급락 miss 완화 가능 — 임계·오버레이 종류에 따라 상이"
            ),
            "v_rebound_hypo": (
                "bull_abstain=anti-V-rebound(관망); bull_to_bear=급락 후 연속 하락 가설 — "
                "둘 다 [HYPO] sandbox only"
            ),
        },
        "track_wall": "no_track_a_live_auto_merge",
    }

    assert_output_path_isolated(out_path.resolve())
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    rec = next(
        (x for x in overlay_results if x.get("overlay") == "prior_day_shock_bull_to_bear_v0"),
        overlay_results[0] if overlay_results else {},
    )
    return {
        "step": "bull_abstain_overlay_ablation",
        "output": _rel(out_path),
        "multilens_baseline_hit_rate": payload.get("multilens_baseline_hit_rate"),
        "best_overlay": (best_overlay_row or {}).get("overlay"),
        "best_sweep_delta_hit_rate": (best_overlay_row or {}).get("delta_hit_rate"),
        "bull_to_bear_recommended_delta": (rec.get("recommended_threshold") or {}).get("delta_hit_rate"),
        "spotlight_6_8": next(
            (s for s in (rec.get("spotlight") or []) if s.get("date") == "2026-06-08"),
            None,
        ),
    }


def _spotlight_for_overlay(
    *,
    rows_in: list[dict[str, Any]],
    overlaid: list[dict[str, Any]],
    prior_map: dict[str, float],
    overnight_map: dict[str, float] | None,
    intraday_drawdown_map: dict[str, float] | None,
    spotlight_dates: list[str],
    range_position_map: dict[str, float] | None = None,
    realized_vol_map: dict[str, float] | None = None,
) -> list[dict[str, Any]]:
    rows_by_date = {str(r.get("eval_date") or "")[:10]: r for r in rows_in if r.get("eval_date")}
    overlaid_by_date = {str(r.get("eval_date") or "")[:10]: r for r in overlaid}
    out: list[dict[str, Any]] = []
    for dk in spotlight_dates:
        base_r = rows_by_date.get(dk)
        ov_r = overlaid_by_date.get(dk)
        if not base_r:
            out.append({"date": dk, "status": "missing_eval_row"})
            continue
        base_pred = str(base_r.get("predicted_direction") or "").strip().lower()
        after_pred = str((ov_r or base_r).get("predicted_direction") or "").strip().lower()
        actual = str(base_r.get("actual_direction") or "").strip().lower()
        pr = prior_map.get(dk)
        ovn = (overnight_map or {}).get(dk)
        dd = (intraday_drawdown_map or {}).get(dk)
        rpos = (range_position_map or {}).get(dk)
        vol = (realized_vol_map or {}).get(dk)
        out.append(
            {
                "date": dk,
                "prior_completed_daily_return_pct": round(pr * 100.0, 4) if pr is not None else None,
                "overnight_gap_pct": round(ovn * 100.0, 4) if ovn is not None else None,
                "intraday_open_to_low_drawdown_pct": round(dd * 100.0, 4) if dd is not None else None,
                "prior_range_position": round(rpos, 4) if rpos is not None else None,
                "realized_vol_5d_pct": round(vol * 100.0, 4) if vol is not None else None,
                "baseline_predicted": base_pred,
                "after_overlay_predicted": after_pred,
                "actual_direction": actual,
                "overlay_modified": base_pred != after_pred,
                "overlay_rule": (ov_r or {}).get("overlay_rule"),
                "baseline_hit": base_pred == actual if actual else None,
                "after_overlay_hit": after_pred == actual if actual else None,
            }
        )
    return out


def run_shock_rebound_guard_ablation_sidecar(
    *,
    recipe: dict[str, Any],
    panel_csv: Path,
    kospi_csv: Path,
    date_from: str,
    date_to: str,
    spotlight_dates: list[str],
    out_path: Path,
    dry_run: bool,
) -> dict[str, Any]:
    """Mild prior shock + V-rebound guard grid + overnight gap [HYPO] on multilens baseline."""
    ablation = (
        recipe.get("shock_rebound_guard_ablation")
        if isinstance(recipe.get("shock_rebound_guard_ablation"), dict)
        else {}
    )
    mild_sweep = list(ablation.get("mild_prior_threshold_sweep") or [-0.04, -0.048, -0.055, -0.06])
    guard_sweep = list(ablation.get("rebound_guard_threshold_sweep") or [-0.065, -0.07, -0.075, -0.08])
    rec_mild = float((ablation.get("recommended_pair") or {}).get("mild") or -0.048)
    rec_guard = float((ablation.get("recommended_pair") or {}).get("guard") or -0.07)
    ovn_sweep = list(ablation.get("overnight_gap_threshold_sweep") or [-0.02, -0.03, -0.04])
    variant_key = str(ablation.get("multilens_variant") or "operational_baseline")

    if dry_run:
        return {
            "step": "shock_rebound_guard_ablation",
            "skipped": True,
            "mild_prior_threshold_sweep": mild_sweep,
            "rebound_guard_threshold_sweep": guard_sweep,
            "output": _rel(out_path),
        }

    if not panel_csv.is_file() or not kospi_csv.is_file():
        return {
            "step": "shock_rebound_guard_ablation",
            "skipped": True,
            "reason": "missing panel or kospi csv",
        }

    from scripts.run_prophecy_restoration_spike import (
        _apply_overlay,
        _eval_directional_hit,
        _overnight_return_by_eval_date,
        _prior_completed_daily_return_by_eval_date,
    )

    rows_in = build_multilens_eval_rows(
        recipe=recipe,
        panel_csv=panel_csv,
        kospi_csv=kospi_csv,
        date_from=date_from,
        date_to=date_to,
        variant_key=variant_key,
    )
    if not rows_in:
        return {
            "step": "shock_rebound_guard_ablation",
            "skipped": True,
            "reason": "no multilens eval rows",
        }

    prior_map = _prior_completed_daily_return_by_eval_date(kospi_csv)
    overnight_map = _overnight_return_by_eval_date(kospi_csv)
    base_rate, base_n, base_hits = _eval_directional_hit(rows_in)

    naive_overlaid, naive_mod = _apply_overlay(
        rows_in,
        overlay="prior_day_shock_bull_to_bear_v0",
        stress_years=set(),
        prior_return_by_date=prior_map,
        prior_return_threshold=-0.048,
    )
    naive_rate, _, _ = _eval_directional_hit(naive_overlaid)
    naive_block = {
        "overlay": "prior_day_shock_bull_to_bear_v0",
        "prior_return_threshold": -0.048,
        "rebound_guard": None,
        "baseline_hit_rate": base_rate,
        "after_overlay_hit_rate": naive_rate,
        "delta_hit_rate": round(float(naive_rate) - float(base_rate), 6)
        if naive_rate is not None and base_rate is not None
        else None,
        "overlay_rows_modified": naive_mod,
        "spotlight": _spotlight_for_overlay(
            rows_in=rows_in,
            overlaid=naive_overlaid,
            prior_map=prior_map,
            overnight_map=overnight_map,
            intraday_drawdown_map=None,
            spotlight_dates=spotlight_dates,
        ),
    }

    grid_rows: list[dict[str, Any]] = []
    best_grid: dict[str, Any] | None = None
    for mild in mild_sweep:
        for guard in guard_sweep:
            mild_f = float(mild)
            guard_f = float(guard)
            if guard_f >= mild_f:
                continue
            overlaid, n_mod = _apply_overlay(
                rows_in,
                overlay="prior_shock_bull_to_bear_rebound_guard_v0",
                stress_years=set(),
                prior_return_by_date=prior_map,
                prior_return_threshold=mild_f,
                rebound_guard_threshold=guard_f,
            )
            ov_rate, ov_n, _ = _eval_directional_hit(overlaid)
            delta = round(float(ov_rate) - float(base_rate), 6) if ov_rate is not None and base_rate is not None else None
            row = {
                "mild_prior_return_threshold": mild_f,
                "mild_prior_return_threshold_pct": round(mild_f * 100.0, 4),
                "rebound_guard_threshold": guard_f,
                "rebound_guard_threshold_pct": round(guard_f * 100.0, 4),
                "baseline_hit_rate": base_rate,
                "after_overlay_hit_rate": ov_rate,
                "delta_hit_rate": delta,
                "overlay_rows_modified": n_mod,
                "n_evaluated": ov_n,
            }
            grid_rows.append(row)
            if delta is not None and (best_grid is None or delta > best_grid.get("delta_hit_rate", -999)):
                best_grid = {**row, "overlay": "prior_shock_bull_to_bear_rebound_guard_v0"}

    rec_overlaid, rec_mod = _apply_overlay(
        rows_in,
        overlay="prior_shock_bull_to_bear_rebound_guard_v0",
        stress_years=set(),
        prior_return_by_date=prior_map,
        prior_return_threshold=rec_mild,
        rebound_guard_threshold=rec_guard,
    )
    rec_rate, _, _ = _eval_directional_hit(rec_overlaid)
    recommended_block = {
        "overlay": "prior_shock_bull_to_bear_rebound_guard_v0",
        "mild_prior_return_threshold": rec_mild,
        "rebound_guard_threshold": rec_guard,
        "baseline_hit_rate": base_rate,
        "after_overlay_hit_rate": rec_rate,
        "delta_hit_rate": round(float(rec_rate) - float(base_rate), 6)
        if rec_rate is not None and base_rate is not None
        else None,
        "overlay_rows_modified": rec_mod,
        "spotlight": _spotlight_for_overlay(
            rows_in=rows_in,
            overlaid=rec_overlaid,
            prior_map=prior_map,
            overnight_map=overnight_map,
            intraday_drawdown_map=None,
            spotlight_dates=spotlight_dates,
        ),
    }

    ovn_sweep_rows: list[dict[str, Any]] = []
    best_overnight: dict[str, Any] | None = None
    for thr in ovn_sweep:
        thr_f = float(thr)
        overlaid, n_mod = _apply_overlay(
            rows_in,
            overlay="overnight_gap_shock_bull_to_bear_v0",
            stress_years=set(),
            prior_return_by_date=prior_map,
            prior_return_threshold=thr_f,
            overnight_return_by_date=overnight_map,
        )
        ov_rate, ov_n, _ = _eval_directional_hit(overlaid)
        delta = round(float(ov_rate) - float(base_rate), 6) if ov_rate is not None and base_rate is not None else None
        row = {
            "overnight_gap_threshold": thr_f,
            "overnight_gap_threshold_pct": round(thr_f * 100.0, 4),
            "baseline_hit_rate": base_rate,
            "after_overlay_hit_rate": ov_rate,
            "delta_hit_rate": delta,
            "overlay_rows_modified": n_mod,
            "n_evaluated": ov_n,
        }
        ovn_sweep_rows.append(row)
        if delta is not None and (best_overnight is None or delta > best_overnight.get("delta_hit_rate", -999)):
            best_overnight = {**row, "overlay": "overnight_gap_shock_bull_to_bear_v0"}

    ovn_rec_overlaid, _ = _apply_overlay(
        rows_in,
        overlay="overnight_gap_shock_bull_to_bear_v0",
        stress_years=set(),
        prior_return_by_date=prior_map,
        prior_return_threshold=ovn_sweep[1] if len(ovn_sweep) > 1 else -0.03,
        overnight_return_by_date=overnight_map,
    )
    ovn_spotlight = _spotlight_for_overlay(
        rows_in=rows_in,
        overlaid=ovn_rec_overlaid,
        prior_map=prior_map,
        overnight_map=overnight_map,
        intraday_drawdown_map=None,
        spotlight_dates=spotlight_dates,
    )

    payload: dict[str, Any] = {
        "schema": "max_hypo_shock_rebound_guard_ablation_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "hypothesis_tag": "[MAX_HYPO][HYPO]",
        "inputs": {
            "panel_csv": _rel(panel_csv),
            "kospi_csv": _rel(kospi_csv),
            "date_from": date_from,
            "date_to": date_to,
            "multilens_variant": variant_key,
            "recommended_pair": {"mild": rec_mild, "guard": rec_guard},
            "n_eval_rows": len(rows_in),
        },
        "multilens_baseline_hit_rate": base_rate,
        "naive_bull_to_bear_at_minus_4_8pct": naive_block,
        "rebound_guard_grid": grid_rows,
        "best_rebound_guard_in_grid": best_grid,
        "recommended_rebound_guard": recommended_block,
        "overnight_gap_sweep": ovn_sweep_rows,
        "best_overnight_gap_in_sweep": best_overnight,
        "overnight_gap_spotlight_mid_threshold": ovn_spotlight,
        "interpretation_ko": {
            "6_8_vs_6_9": (
                "mild prior(~-5.5%)로 6/8 bull→bear 가능; guard(~-7%)로 6/9 전일 -8.3% 급락 시 "
                "오버레이 스킵 → V-rebound bull 유지"
            ),
            "6_8_intraday": (
                "6/8 당일 -8.3%는 장중; overnight gap ~-1.4%만으로는 당일 shock 미포착 — "
                "prior completed 또는 장중 프록시 별도 [HYPO]"
            ),
        },
        "track_wall": "no_track_a_live_auto_merge",
    }

    assert_output_path_isolated(out_path.resolve())
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    spot_rec = next((s for s in recommended_block["spotlight"] if s.get("date") == "2026-06-08"), None)
    return {
        "step": "shock_rebound_guard_ablation",
        "output": _rel(out_path),
        "multilens_baseline_hit_rate": base_rate,
        "naive_minus_4_8_delta": naive_block.get("delta_hit_rate"),
        "recommended_delta": recommended_block.get("delta_hit_rate"),
        "best_grid_delta": (best_grid or {}).get("delta_hit_rate"),
        "spotlight_6_8_recommended": spot_rec,
        "spotlight_6_9_recommended": next(
            (s for s in recommended_block["spotlight"] if s.get("date") == "2026-06-09"),
            None,
        ),
    }


def _load_science_core_shock_discordant_pointer(
    artifact_path: Path,
    spotlight_dates: list[str],
) -> dict[str, Any]:
    if not artifact_path.is_file():
        return {"present": False, "path": _rel(artifact_path)}
    try:
        doc = json.loads(artifact_path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {"present": False, "path": _rel(artifact_path), "reason": "invalid_json"}
    rows = doc.get("rows") if isinstance(doc.get("rows"), list) else []
    by_date = {
        str((r.get("eval_date") or r.get("date") or ""))[:10]: r
        for r in rows
        if isinstance(r, dict)
    }
    spotlight = []
    for dk in spotlight_dates:
        row = by_date.get(dk)
        if not row:
            spotlight.append({"date": dk, "status": "missing_in_science_core_report"})
            continue
        spotlight.append(
            {
                "date": dk,
                "actual_direction": row.get("actual_direction"),
                "predictions": row.get("predictions"),
                "shock_move_bps": row.get("shock_move_bps"),
                "discordant": row.get("discordant"),
            }
        )
    return {
        "present": True,
        "path": _rel(artifact_path),
        "schema": doc.get("schema"),
        "macro_diversity_audit": doc.get("macro_diversity_audit"),
        "spotlight": spotlight,
        "note_ko": "Science Core shock discordant report — reference only; not auto-merged to Track A.",
    }


def run_intraday_shock_proxy_ablation_sidecar(
    *,
    recipe: dict[str, Any],
    panel_csv: Path,
    kospi_csv: Path,
    date_from: str,
    date_to: str,
    spotlight_dates: list[str],
    out_path: Path,
    dry_run: bool,
) -> dict[str, Any]:
    """Intraday oracle ceiling + session-open composite [HYPO] on multilens baseline."""
    ablation = (
        recipe.get("intraday_shock_proxy_ablation")
        if isinstance(recipe.get("intraday_shock_proxy_ablation"), dict)
        else {}
    )
    oracle_sweep = list(ablation.get("oracle_drawdown_threshold_sweep") or [0.04, 0.05, 0.06, 0.07])
    ovn_sweep = list(ablation.get("composite_overnight_threshold_sweep") or [-0.015, -0.02, -0.025])
    rec = ablation.get("recommended_composite") if isinstance(ablation.get("recommended_composite"), dict) else {}
    rec_mild = float(rec.get("mild") or -0.048)
    rec_guard = float(rec.get("guard") or -0.07)
    rec_ovn = float(rec.get("overnight") or -0.02)
    oracle_rec = float(ablation.get("oracle_drawdown_recommended") or 0.05)
    variant_key = str(ablation.get("multilens_variant") or "operational_baseline")
    sc_path = ROOT / str(
        ablation.get("science_core_artifact_ref") or "reports/science_core_shock_discordant_day_v1_latest.json"
    )

    if dry_run:
        return {
            "step": "intraday_shock_proxy_ablation",
            "skipped": True,
            "oracle_drawdown_threshold_sweep": oracle_sweep,
            "output": _rel(out_path),
        }

    if not panel_csv.is_file() or not kospi_csv.is_file():
        return {"step": "intraday_shock_proxy_ablation", "skipped": True, "reason": "missing panel or kospi"}

    from scripts.run_prophecy_restoration_spike import (
        _apply_overlay,
        _eval_directional_hit,
        _intraday_open_to_low_drawdown_by_eval_date,
        _overnight_return_by_eval_date,
        _prior_completed_daily_return_by_eval_date,
    )

    rows_in = build_multilens_eval_rows(
        recipe=recipe,
        panel_csv=panel_csv,
        kospi_csv=kospi_csv,
        date_from=date_from,
        date_to=date_to,
        variant_key=variant_key,
    )
    if not rows_in:
        return {"step": "intraday_shock_proxy_ablation", "skipped": True, "reason": "no multilens eval rows"}

    prior_map = _prior_completed_daily_return_by_eval_date(kospi_csv)
    overnight_map = _overnight_return_by_eval_date(kospi_csv)
    intraday_map = _intraday_open_to_low_drawdown_by_eval_date(kospi_csv)
    base_rate, _, _ = _eval_directional_hit(rows_in)

    oracle_sweep_rows: list[dict[str, Any]] = []
    best_oracle: dict[str, Any] | None = None
    for thr in oracle_sweep:
        thr_f = float(thr)
        overlaid, n_mod = _apply_overlay(
            rows_in,
            overlay="intraday_open_to_low_oracle_bull_to_bear_v0",
            stress_years=set(),
            prior_return_by_date=prior_map,
            prior_return_threshold=thr_f,
            intraday_drawdown_by_date=intraday_map,
        )
        ov_rate, ov_n, _ = _eval_directional_hit(overlaid)
        delta = round(float(ov_rate) - float(base_rate), 6) if ov_rate is not None and base_rate is not None else None
        row = {
            "intraday_drawdown_threshold": thr_f,
            "intraday_drawdown_threshold_pct": round(thr_f * 100.0, 4),
            "baseline_hit_rate": base_rate,
            "after_overlay_hit_rate": ov_rate,
            "delta_hit_rate": delta,
            "overlay_rows_modified": n_mod,
            "n_evaluated": ov_n,
            "causal_at_open": False,
            "oracle_note": "eval_day_low_lookahead_not_causal",
        }
        oracle_sweep_rows.append(row)
        if delta is not None and (best_oracle is None or delta > best_oracle.get("delta_hit_rate", -999)):
            best_oracle = {**row, "overlay": "intraday_open_to_low_oracle_bull_to_bear_v0"}

    oracle_overlaid, oracle_mod = _apply_overlay(
        rows_in,
        overlay="intraday_open_to_low_oracle_bull_to_bear_v0",
        stress_years=set(),
        prior_return_by_date=prior_map,
        prior_return_threshold=oracle_rec,
        intraday_drawdown_by_date=intraday_map,
    )
    oracle_rate, _, _ = _eval_directional_hit(oracle_overlaid)
    oracle_recommended = {
        "overlay": "intraday_open_to_low_oracle_bull_to_bear_v0",
        "intraday_drawdown_threshold": oracle_rec,
        "baseline_hit_rate": base_rate,
        "after_overlay_hit_rate": oracle_rate,
        "delta_hit_rate": round(float(oracle_rate) - float(base_rate), 6)
        if oracle_rate is not None and base_rate is not None
        else None,
        "overlay_rows_modified": oracle_mod,
        "causal_at_open": False,
        "spotlight": _spotlight_for_overlay(
            rows_in=rows_in,
            overlaid=oracle_overlaid,
            prior_map=prior_map,
            overnight_map=overnight_map,
            intraday_drawdown_map=intraday_map,
            spotlight_dates=spotlight_dates,
        ),
    }

    composite_sweep_rows: list[dict[str, Any]] = []
    best_composite: dict[str, Any] | None = None
    for ovn_thr in ovn_sweep:
        ovn_f = float(ovn_thr)
        overlaid, n_mod = _apply_overlay(
            rows_in,
            overlay="session_open_composite_bull_to_bear_rebound_guard_v0",
            stress_years=set(),
            prior_return_by_date=prior_map,
            prior_return_threshold=rec_mild,
            rebound_guard_threshold=rec_guard,
            overnight_return_by_date=overnight_map,
            session_open_composite_overnight_threshold=ovn_f,
        )
        ov_rate, ov_n, _ = _eval_directional_hit(overlaid)
        delta = round(float(ov_rate) - float(base_rate), 6) if ov_rate is not None and base_rate is not None else None
        row = {
            "mild_prior_return_threshold": rec_mild,
            "rebound_guard_threshold": rec_guard,
            "overnight_gap_threshold": ovn_f,
            "overnight_gap_threshold_pct": round(ovn_f * 100.0, 4),
            "baseline_hit_rate": base_rate,
            "after_overlay_hit_rate": ov_rate,
            "delta_hit_rate": delta,
            "overlay_rows_modified": n_mod,
            "n_evaluated": ov_n,
            "causal_at_open": True,
        }
        composite_sweep_rows.append(row)
        if delta is not None and (best_composite is None or delta > best_composite.get("delta_hit_rate", -999)):
            best_composite = {**row, "overlay": "session_open_composite_bull_to_bear_rebound_guard_v0"}

    composite_overlaid, composite_mod = _apply_overlay(
        rows_in,
        overlay="session_open_composite_bull_to_bear_rebound_guard_v0",
        stress_years=set(),
        prior_return_by_date=prior_map,
        prior_return_threshold=rec_mild,
        rebound_guard_threshold=rec_guard,
        overnight_return_by_date=overnight_map,
        session_open_composite_overnight_threshold=rec_ovn,
    )
    composite_rate, _, _ = _eval_directional_hit(composite_overlaid)
    composite_recommended = {
        "overlay": "session_open_composite_bull_to_bear_rebound_guard_v0",
        "mild_prior_return_threshold": rec_mild,
        "rebound_guard_threshold": rec_guard,
        "overnight_gap_threshold": rec_ovn,
        "baseline_hit_rate": base_rate,
        "after_overlay_hit_rate": composite_rate,
        "delta_hit_rate": round(float(composite_rate) - float(base_rate), 6)
        if composite_rate is not None and base_rate is not None
        else None,
        "overlay_rows_modified": composite_mod,
        "causal_at_open": True,
        "spotlight": _spotlight_for_overlay(
            rows_in=rows_in,
            overlaid=composite_overlaid,
            prior_map=prior_map,
            overnight_map=overnight_map,
            intraday_drawdown_map=intraday_map,
            spotlight_dates=spotlight_dates,
        ),
    }

    payload: dict[str, Any] = {
        "schema": "max_hypo_intraday_shock_proxy_ablation_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "hypothesis_tag": "[MAX_HYPO][HYPO]",
        "inputs": {
            "panel_csv": _rel(panel_csv),
            "kospi_csv": _rel(kospi_csv),
            "date_from": date_from,
            "date_to": date_to,
            "multilens_variant": variant_key,
            "n_eval_rows": len(rows_in),
        },
        "multilens_baseline_hit_rate": base_rate,
        "intraday_oracle_sweep": oracle_sweep_rows,
        "best_intraday_oracle_in_sweep": best_oracle,
        "recommended_intraday_oracle": oracle_recommended,
        "session_open_composite_sweep": composite_sweep_rows,
        "best_session_open_composite_in_sweep": best_composite,
        "recommended_session_open_composite": composite_recommended,
        "science_core_shock_discordant_pointer": _load_science_core_shock_discordant_pointer(
            sc_path, spotlight_dates
        ),
        "interpretation_ko": {
            "oracle_ceiling": (
                "intraday open→low oracle는 eval-day low 사용(장중 인지 가정) — "
                "Track A 인과 경로 아님; 상한선 벤치만"
            ),
            "6_8_open_gap": "6/8 overnight ~-1.4% — composite overnight 단독으론 miss; prior mild 또는 oracle",
            "6_8_drawdown": "6/8 open→low ~7.5% — oracle 5%면 bull→bear 적중 가능",
        },
        "track_wall": "no_track_a_live_auto_merge",
    }

    assert_output_path_isolated(out_path.resolve())
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    spot_oracle = next(
        (s for s in oracle_recommended["spotlight"] if s.get("date") == "2026-06-08"),
        None,
    )
    return {
        "step": "intraday_shock_proxy_ablation",
        "output": _rel(out_path),
        "multilens_baseline_hit_rate": base_rate,
        "oracle_recommended_delta": oracle_recommended.get("delta_hit_rate"),
        "composite_recommended_delta": composite_recommended.get("delta_hit_rate"),
        "spotlight_6_8_oracle": spot_oracle,
        "spotlight_6_8_composite": next(
            (s for s in composite_recommended["spotlight"] if s.get("date") == "2026-06-08"),
            None,
        ),
    }


def _chronological_walkforward_slices(
    rows: list[dict[str, Any]], n_folds: int
) -> list[tuple[set[str], set[str]]]:
    dates = sorted({str(r.get("eval_date") or "")[:10] for r in rows if r.get("eval_date")})
    if len(dates) < max(8, n_folds * 2):
        return []
    fold_size = len(dates) // n_folds
    slices: list[tuple[set[str], set[str]]] = []
    for i in range(n_folds):
        test_start = i * fold_size
        test_end = len(dates) if i == n_folds - 1 else (i + 1) * fold_size
        test_dates = set(dates[test_start:test_end])
        train_dates = set(dates[:test_start])
        if train_dates and test_dates:
            slices.append((train_dates, test_dates))
    return slices


def _filter_rows_by_dates(rows: list[dict[str, Any]], dates: set[str]) -> list[dict[str, Any]]:
    return [r for r in rows if str(r.get("eval_date") or "")[:10] in dates]


def _overlay_delta_on_rows(
    rows: list[dict[str, Any]],
    *,
    overlay: str,
    prior_map: dict[str, float],
    overnight_map: dict[str, float],
    intraday_map: dict[str, float] | None,
    prior_return_threshold: float,
    rebound_guard_threshold: float | None = None,
    session_open_composite_overnight_threshold: float | None = None,
    realized_vol_map: dict[str, float] | None = None,
    vol_regime_threshold: float | None = None,
    range_position_map: dict[str, float] | None = None,
    prior_range_low_threshold: float | None = None,
    overnight_gap_rebound_skip_threshold: float | None = None,
    range_soft_cap_for_range_only_leg: float | None = None,
) -> tuple[float | None, float | None, float | None, list[dict[str, Any]]]:
    from scripts.run_prophecy_restoration_spike import _apply_overlay, _eval_directional_hit

    base_rate, _, _ = _eval_directional_hit(rows)
    overlaid, _ = _apply_overlay(
        rows,
        overlay=overlay,
        stress_years=set(),
        prior_return_by_date=prior_map,
        prior_return_threshold=prior_return_threshold,
        rebound_guard_threshold=rebound_guard_threshold,
        overnight_return_by_date=overnight_map,
        session_open_composite_overnight_threshold=session_open_composite_overnight_threshold,
        intraday_drawdown_by_date=intraday_map,
        realized_vol_by_date=realized_vol_map,
        vol_regime_threshold=vol_regime_threshold,
        prior_range_position_by_date=range_position_map,
        prior_range_low_threshold=prior_range_low_threshold,
        overnight_gap_rebound_skip_threshold=overnight_gap_rebound_skip_threshold,
        range_soft_cap_for_range_only_leg=range_soft_cap_for_range_only_leg,
    )
    ov_rate, _, _ = _eval_directional_hit(overlaid)
    delta = (
        round(float(ov_rate) - float(base_rate), 6)
        if ov_rate is not None and base_rate is not None
        else None
    )
    return base_rate, ov_rate, delta, overlaid


def run_causal_open_limit_ablation_sidecar(
    *,
    recipe: dict[str, Any],
    panel_csv: Path,
    kospi_csv: Path,
    date_from: str,
    date_to: str,
    spotlight_dates: list[str],
    out_path: Path,
    dry_run: bool,
) -> dict[str, Any]:
    """Causal-at-open tier ladder vs oracle ceiling + blocked WF on composite [HYPO]."""
    ablation = (
        recipe.get("causal_open_limit_ablation")
        if isinstance(recipe.get("causal_open_limit_ablation"), dict)
        else {}
    )
    n_folds = int(ablation.get("n_walkforward_folds") or 4)
    ovn_only = float(ablation.get("tier_overnight_only_threshold") or -0.02)
    rec_prior = ablation.get("tier_prior_rebound_guard") if isinstance(ablation.get("tier_prior_rebound_guard"), dict) else {}
    rec_comp = ablation.get("tier_composite_recommended") if isinstance(ablation.get("tier_composite_recommended"), dict) else {}
    mild_t = float(rec_prior.get("mild") or -0.048)
    guard_t = float(rec_prior.get("guard") or -0.07)
    comp_mild = float(rec_comp.get("mild") or mild_t)
    comp_guard = float(rec_comp.get("guard") or guard_t)
    comp_ovn = float(rec_comp.get("overnight") or -0.02)
    oracle_t = float(ablation.get("tier_oracle_drawdown_threshold") or 0.05)
    mild_sweep = list(ablation.get("composite_walkforward_mild_sweep") or [-0.04, -0.048, -0.055, -0.06])
    guard_sweep = list(ablation.get("composite_walkforward_guard_sweep") or [-0.065, -0.07, -0.075, -0.08])
    ovn_sweep = list(ablation.get("composite_walkforward_overnight_sweep") or [-0.015, -0.02, -0.025])
    variant_key = str(ablation.get("multilens_variant") or "operational_baseline")

    if dry_run:
        return {
            "step": "causal_open_limit_ablation",
            "skipped": True,
            "n_walkforward_folds": n_folds,
            "output": _rel(out_path),
        }

    if not panel_csv.is_file() or not kospi_csv.is_file():
        return {"step": "causal_open_limit_ablation", "skipped": True, "reason": "missing panel or kospi"}

    from scripts.run_prophecy_restoration_spike import (
        _eval_directional_hit,
        _intraday_open_to_low_drawdown_by_eval_date,
        _overnight_return_by_eval_date,
        _prior_completed_daily_return_by_eval_date,
    )

    rows_in = build_multilens_eval_rows(
        recipe=recipe,
        panel_csv=panel_csv,
        kospi_csv=kospi_csv,
        date_from=date_from,
        date_to=date_to,
        variant_key=variant_key,
    )
    if not rows_in:
        return {"step": "causal_open_limit_ablation", "skipped": True, "reason": "no multilens eval rows"}

    prior_map = _prior_completed_daily_return_by_eval_date(kospi_csv)
    overnight_map = _overnight_return_by_eval_date(kospi_csv)
    intraday_map = _intraday_open_to_low_drawdown_by_eval_date(kospi_csv)
    base_rate, base_n, _ = _eval_directional_hit(rows_in)

    tier_specs: list[dict[str, Any]] = [
        {
            "tier_id": "T0_baseline",
            "causal_at_open": True,
            "overlay": None,
        },
        {
            "tier_id": "T1_overnight_only",
            "causal_at_open": True,
            "overlay": "overnight_gap_shock_bull_to_bear_v0",
            "prior_return_threshold": ovn_only,
        },
        {
            "tier_id": "T2_prior_rebound_guard",
            "causal_at_open": True,
            "overlay": "prior_shock_bull_to_bear_rebound_guard_v0",
            "prior_return_threshold": mild_t,
            "rebound_guard_threshold": guard_t,
        },
        {
            "tier_id": "T3_composite_recommended",
            "causal_at_open": True,
            "overlay": "session_open_composite_bull_to_bear_rebound_guard_v0",
            "prior_return_threshold": comp_mild,
            "rebound_guard_threshold": comp_guard,
            "session_open_composite_overnight_threshold": comp_ovn,
        },
        {
            "tier_id": "T4_oracle_ceiling",
            "causal_at_open": False,
            "overlay": "intraday_open_to_low_oracle_bull_to_bear_v0",
            "prior_return_threshold": oracle_t,
        },
    ]

    tier_rows: list[dict[str, Any]] = []
    for spec in tier_specs:
        if spec.get("overlay") is None:
            tier_rows.append(
                {
                    **spec,
                    "baseline_hit_rate": base_rate,
                    "after_overlay_hit_rate": base_rate,
                    "delta_hit_rate": 0.0,
                    "n_evaluated": base_n,
                    "spotlight": _spotlight_for_overlay(
                        rows_in=rows_in,
                        overlaid=rows_in,
                        prior_map=prior_map,
                        overnight_map=overnight_map,
                        intraday_drawdown_map=intraday_map,
                        spotlight_dates=spotlight_dates,
                    ),
                }
            )
            continue
        br, ov, delta, overlaid = _overlay_delta_on_rows(
            rows_in,
            overlay=str(spec["overlay"]),
            prior_map=prior_map,
            overnight_map=overnight_map,
            intraday_map=intraday_map if spec["overlay"] == "intraday_open_to_low_oracle_bull_to_bear_v0" else None,
            prior_return_threshold=float(spec["prior_return_threshold"]),
            rebound_guard_threshold=spec.get("rebound_guard_threshold"),
            session_open_composite_overnight_threshold=spec.get("session_open_composite_overnight_threshold"),
        )
        tier_rows.append(
            {
                **spec,
                "baseline_hit_rate": br,
                "after_overlay_hit_rate": ov,
                "delta_hit_rate": delta,
                "n_evaluated": base_n,
                "spotlight": _spotlight_for_overlay(
                    rows_in=rows_in,
                    overlaid=overlaid,
                    prior_map=prior_map,
                    overnight_map=overnight_map,
                    intraday_drawdown_map=intraday_map,
                    spotlight_dates=spotlight_dates,
                ),
            }
        )

    spotlight_limits: list[dict[str, Any]] = []
    for dk in spotlight_dates:
        ovn = overnight_map.get(dk)
        pr = prior_map.get(dk)
        dd = intraday_map.get(dk)
        spotlight_limits.append(
            {
                "date": dk,
                "overnight_gap_pct": round(ovn * 100.0, 4) if ovn is not None else None,
                "prior_completed_daily_return_pct": round(pr * 100.0, 4) if pr is not None else None,
                "intraday_open_to_low_drawdown_pct": round(dd * 100.0, 4) if dd is not None else None,
                "overnight_only_fires_at_tier_threshold": (
                    ovn is not None and ovn <= ovn_only if ovn is not None else None
                ),
                "prior_mild_fires_at_tier_threshold": (
                    pr is not None and pr <= mild_t and pr > guard_t
                ),
                "oracle_fires_at_5pct": dd is not None and dd >= oracle_t if dd is not None else None,
                "causal_gap_note_ko": (
                    "시가 갭만으로는 6/8 급락 미포착; 전일 mild 또는 장중 oracle 필요"
                    if dk == "2026-06-08"
                    else None
                ),
            }
        )

    wf_slices = _chronological_walkforward_slices(rows_in, n_folds)
    wf_fold_rows: list[dict[str, Any]] = []
    train_deltas: list[float] = []
    test_deltas: list[float] = []
    test_oracle_deltas: list[float] = []

    for fold_idx, (train_dates, test_dates) in enumerate(wf_slices):
        train_rows = _filter_rows_by_dates(rows_in, train_dates)
        test_rows = _filter_rows_by_dates(rows_in, test_dates)
        best: dict[str, Any] | None = None
        for mild in mild_sweep:
            for guard in guard_sweep:
                for ovn_thr in ovn_sweep:
                    _, _, train_delta, _ = _overlay_delta_on_rows(
                        train_rows,
                        overlay="session_open_composite_bull_to_bear_rebound_guard_v0",
                        prior_map=prior_map,
                        overnight_map=overnight_map,
                        intraday_map=None,
                        prior_return_threshold=float(mild),
                        rebound_guard_threshold=float(guard),
                        session_open_composite_overnight_threshold=float(ovn_thr),
                    )
                    if train_delta is None:
                        continue
                    cand = {
                        "mild": float(mild),
                        "guard": float(guard),
                        "overnight": float(ovn_thr),
                        "train_delta_hit_rate": train_delta,
                    }
                    if best is None or train_delta > best["train_delta_hit_rate"]:
                        best = cand
        if best is None:
            continue
        _, _, test_delta, _ = _overlay_delta_on_rows(
            test_rows,
            overlay="session_open_composite_bull_to_bear_rebound_guard_v0",
            prior_map=prior_map,
            overnight_map=overnight_map,
            intraday_map=None,
            prior_return_threshold=best["mild"],
            rebound_guard_threshold=best["guard"],
            session_open_composite_overnight_threshold=best["overnight"],
        )
        _, _, oracle_test_delta, _ = _overlay_delta_on_rows(
            test_rows,
            overlay="intraday_open_to_low_oracle_bull_to_bear_v0",
            prior_map=prior_map,
            overnight_map=overnight_map,
            intraday_map=intraday_map,
            prior_return_threshold=oracle_t,
        )
        wf_fold_rows.append(
            {
                "fold": fold_idx,
                "n_train_dates": len(train_dates),
                "n_test_dates": len(test_dates),
                "selected_on_train": best,
                "test_delta_hit_rate": test_delta,
                "test_oracle_delta_hit_rate": oracle_test_delta,
            }
        )
        train_deltas.append(float(best["train_delta_hit_rate"]))
        if test_delta is not None:
            test_deltas.append(float(test_delta))
        if oracle_test_delta is not None:
            test_oracle_deltas.append(float(oracle_test_delta))

    wf_summary = {
        "n_folds_effective": len(wf_fold_rows),
        "mean_train_delta_hit_rate": round(sum(train_deltas) / len(train_deltas), 6) if train_deltas else None,
        "mean_test_delta_hit_rate": round(sum(test_deltas) / len(test_deltas), 6) if test_deltas else None,
        "mean_test_oracle_delta_hit_rate": round(sum(test_oracle_deltas) / len(test_oracle_deltas), 6)
        if test_oracle_deltas
        else None,
        "oracle_minus_composite_test_gap_pp": round(
            (sum(test_oracle_deltas) / len(test_oracle_deltas))
            - (sum(test_deltas) / len(test_deltas)),
            6,
        )
        if test_deltas and test_oracle_deltas
        else None,
        "folds": wf_fold_rows,
        "note_ko": "train에서 grid 최적 → test 평가; in-sample 낙관 편향 가능 [HYPO]",
    }

    payload: dict[str, Any] = {
        "schema": "max_hypo_causal_open_limit_ablation_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "hypothesis_tag": "[MAX_HYPO][HYPO]",
        "multilens_baseline_hit_rate": base_rate,
        "causal_tier_ladder": tier_rows,
        "spotlight_causal_limits": spotlight_limits,
        "composite_blocked_walkforward": wf_summary,
        "interpretation_ko": {
            "T1_overnight": "시가 갭 −2%만으론 6/8(갭 ~−1.4%) 미발동 — 장중 충격과 분리",
            "T2_prior": "전일 mild+가드로 6/8·6/9 스포트라이트 가능; 전체 창 Δ는 음수일 수 있음",
            "T3_composite": "전일 OR 갭 트리거 — 인과 가능; 이번 253일 창에서 Δ 양수 가능",
            "T4_oracle": "장중 저가 oracle — Track A 인과 경로 아님; composite 대비 상한선",
            "walkforward": "fold별 train grid → test; mean_test가 mean_train보다 낮으면 과적합 신호",
        },
        "track_wall": "no_track_a_live_auto_merge",
    }

    assert_output_path_isolated(out_path.resolve())
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    t1 = next((t for t in tier_rows if t["tier_id"] == "T1_overnight_only"), {})
    t3 = next((t for t in tier_rows if t["tier_id"] == "T3_composite_recommended"), {})
    t4 = next((t for t in tier_rows if t["tier_id"] == "T4_oracle_ceiling"), {})
    return {
        "step": "causal_open_limit_ablation",
        "output": _rel(out_path),
        "multilens_baseline_hit_rate": base_rate,
        "tier_overnight_delta": t1.get("delta_hit_rate"),
        "tier_composite_delta": t3.get("delta_hit_rate"),
        "tier_oracle_delta": t4.get("delta_hit_rate"),
        "wf_mean_test_delta": wf_summary.get("mean_test_delta_hit_rate"),
        "wf_oracle_minus_composite_gap_pp": wf_summary.get("oracle_minus_composite_test_gap_pp"),
    }


def run_causal_vol_range_proxy_ablation_sidecar(
    *,
    recipe: dict[str, Any],
    panel_csv: Path,
    kospi_csv: Path,
    date_from: str,
    date_to: str,
    spotlight_dates: list[str],
    out_path: Path,
    dry_run: bool,
) -> dict[str, Any]:
    """Prior-range-low + vol-gated composite + conservative composite WF [HYPO]."""
    ablation = (
        recipe.get("causal_vol_range_proxy_ablation")
        if isinstance(recipe.get("causal_vol_range_proxy_ablation"), dict)
        else {}
    )
    n_folds = int(ablation.get("n_walkforward_folds") or 4)
    mild = float((ablation.get("shared_rebound_guard") or {}).get("mild") or -0.048)
    guard = float((ablation.get("shared_rebound_guard") or {}).get("guard") or -0.07)
    ovn_aggressive = float(ablation.get("composite_overnight_aggressive") or -0.02)
    ovn_conservative = float(ablation.get("composite_overnight_conservative") or -0.025)
    vol_rec = float(ablation.get("vol_regime_threshold_recommended") or 0.03)
    range_sweep = list(ablation.get("prior_range_low_threshold_sweep") or [0.10, 0.15, 0.20, 0.25])
    range_rec = float(ablation.get("prior_range_low_threshold_recommended") or 0.15)
    variant_key = str(ablation.get("multilens_variant") or "operational_baseline")

    if dry_run:
        return {
            "step": "causal_vol_range_proxy_ablation",
            "skipped": True,
            "output": _rel(out_path),
        }

    if not panel_csv.is_file() or not kospi_csv.is_file():
        return {"step": "causal_vol_range_proxy_ablation", "skipped": True, "reason": "missing panel or kospi"}

    from scripts.run_prophecy_restoration_spike import (
        _eval_directional_hit,
        _prior_completed_daily_return_by_eval_date,
        _prior_range_position_by_eval_date,
        _overnight_return_by_eval_date,
        _realized_vol_5d_by_eval_date,
    )

    rows_in = build_multilens_eval_rows(
        recipe=recipe,
        panel_csv=panel_csv,
        kospi_csv=kospi_csv,
        date_from=date_from,
        date_to=date_to,
        variant_key=variant_key,
    )
    if not rows_in:
        return {"step": "causal_vol_range_proxy_ablation", "skipped": True, "reason": "no multilens eval rows"}

    prior_map = _prior_completed_daily_return_by_eval_date(kospi_csv)
    overnight_map = _overnight_return_by_eval_date(kospi_csv)
    range_map = _prior_range_position_by_eval_date(kospi_csv)
    vol_map = _realized_vol_5d_by_eval_date(kospi_csv)
    base_rate, base_n, _ = _eval_directional_hit(rows_in)

    def _spotlight(overlaid: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return _spotlight_for_overlay(
            rows_in=rows_in,
            overlaid=overlaid,
            prior_map=prior_map,
            overnight_map=overnight_map,
            intraday_drawdown_map=None,
            spotlight_dates=spotlight_dates,
            range_position_map=range_map,
            realized_vol_map=vol_map,
        )

    tier_specs: list[dict[str, Any]] = [
        {
            "tier_id": "T3b_composite_conservative",
            "overlay": "session_open_composite_bull_to_bear_rebound_guard_v0",
            "prior_return_threshold": mild,
            "rebound_guard_threshold": guard,
            "session_open_composite_overnight_threshold": ovn_conservative,
        },
        {
            "tier_id": "T5_prior_range_low_open",
            "overlay": "prior_range_low_open_bull_to_bear_rebound_guard_v0",
            "prior_return_threshold": mild,
            "rebound_guard_threshold": guard,
            "prior_range_low_threshold": range_rec,
        },
        {
            "tier_id": "T6_vol_gated_composite_conservative",
            "overlay": "vol_gated_session_open_composite_bull_to_bear_rebound_guard_v0",
            "prior_return_threshold": mild,
            "rebound_guard_threshold": guard,
            "session_open_composite_overnight_threshold": ovn_conservative,
            "vol_regime_threshold": vol_rec,
        },
    ]

    tier_rows: list[dict[str, Any]] = []
    for spec in tier_specs:
        br, ov, delta, overlaid = _overlay_delta_on_rows(
            rows_in,
            overlay=str(spec["overlay"]),
            prior_map=prior_map,
            overnight_map=overnight_map,
            intraday_map=None,
            prior_return_threshold=float(spec["prior_return_threshold"]),
            rebound_guard_threshold=spec.get("rebound_guard_threshold"),
            session_open_composite_overnight_threshold=spec.get("session_open_composite_overnight_threshold"),
            realized_vol_map=vol_map if "vol_gated" in spec["overlay"] else None,
            vol_regime_threshold=spec.get("vol_regime_threshold"),
            range_position_map=range_map if "prior_range_low" in spec["overlay"] else None,
            prior_range_low_threshold=spec.get("prior_range_low_threshold"),
        )
        tier_rows.append(
            {
                **spec,
                "causal_at_open": True,
                "baseline_hit_rate": br,
                "after_overlay_hit_rate": ov,
                "delta_hit_rate": delta,
                "n_evaluated": base_n,
                "spotlight": _spotlight(overlaid),
            }
        )

    range_sweep_rows: list[dict[str, Any]] = []
    best_range: dict[str, Any] | None = None
    for thr in range_sweep:
        thr_f = float(thr)
        _, _, delta, _ = _overlay_delta_on_rows(
            rows_in,
            overlay="prior_range_low_open_bull_to_bear_rebound_guard_v0",
            prior_map=prior_map,
            overnight_map=overnight_map,
            intraday_map=None,
            prior_return_threshold=mild,
            rebound_guard_threshold=guard,
            range_position_map=range_map,
            prior_range_low_threshold=thr_f,
        )
        row = {
            "prior_range_low_threshold": thr_f,
            "baseline_hit_rate": base_rate,
            "delta_hit_rate": delta,
        }
        range_sweep_rows.append(row)
        if delta is not None and (best_range is None or delta > best_range.get("delta_hit_rate", -999)):
            best_range = row

    wf_slices = _chronological_walkforward_slices(rows_in, n_folds)
    conservative_folds: list[dict[str, Any]] = []
    aggressive_folds: list[dict[str, Any]] = []
    cons_test: list[float] = []
    aggr_test: list[float] = []

    for fold_idx, (train_dates, test_dates) in enumerate(wf_slices):
        test_rows = _filter_rows_by_dates(rows_in, test_dates)
        _, _, cons_delta, _ = _overlay_delta_on_rows(
            test_rows,
            overlay="session_open_composite_bull_to_bear_rebound_guard_v0",
            prior_map=prior_map,
            overnight_map=overnight_map,
            intraday_map=None,
            prior_return_threshold=mild,
            rebound_guard_threshold=guard,
            session_open_composite_overnight_threshold=ovn_conservative,
        )
        _, _, aggr_delta, _ = _overlay_delta_on_rows(
            test_rows,
            overlay="session_open_composite_bull_to_bear_rebound_guard_v0",
            prior_map=prior_map,
            overnight_map=overnight_map,
            intraday_map=None,
            prior_return_threshold=mild,
            rebound_guard_threshold=guard,
            session_open_composite_overnight_threshold=ovn_aggressive,
        )
        conservative_folds.append(
            {"fold": fold_idx, "n_test_dates": len(test_dates), "test_delta_hit_rate": cons_delta}
        )
        aggressive_folds.append(
            {"fold": fold_idx, "n_test_dates": len(test_dates), "test_delta_hit_rate": aggr_delta}
        )
        if cons_delta is not None:
            cons_test.append(float(cons_delta))
        if aggr_delta is not None:
            aggr_test.append(float(aggr_delta))

    wf_compare = {
        "n_folds_effective": len(conservative_folds),
        "fixed_mild": mild,
        "fixed_guard": guard,
        "conservative_overnight": ovn_conservative,
        "aggressive_overnight": ovn_aggressive,
        "mean_test_delta_conservative": round(sum(cons_test) / len(cons_test), 6) if cons_test else None,
        "mean_test_delta_aggressive": round(sum(aggr_test) / len(aggr_test), 6) if aggr_test else None,
        "conservative_minus_aggressive_test_pp": round(
            (sum(cons_test) / len(cons_test)) - (sum(aggr_test) / len(aggr_test)), 6
        )
        if cons_test and aggr_test
        else None,
        "conservative_folds": conservative_folds,
        "aggressive_folds": aggressive_folds,
        "note_ko": "고정 mild/guard; overnight만 −2.5% vs −2.0% OOS 비교",
    }

    spotlight_features = []
    for dk in spotlight_dates:
        rpos = range_map.get(dk)
        vol = vol_map.get(dk)
        spotlight_features.append(
            {
                "date": dk,
                "prior_range_position": round(rpos, 4) if rpos is not None else None,
                "realized_vol_5d_pct": round(vol * 100.0, 4) if vol is not None else None,
                "range_low_fires_at_0_15": rpos is not None and rpos <= range_rec,
                "vol_regime_fires_at_3pct": vol is not None and vol >= vol_rec,
            }
        )

    payload: dict[str, Any] = {
        "schema": "max_hypo_causal_vol_range_proxy_ablation_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "hypothesis_tag": "[MAX_HYPO][HYPO]",
        "multilens_baseline_hit_rate": base_rate,
        "causal_proxy_tiers": tier_rows,
        "prior_range_low_threshold_sweep": range_sweep_rows,
        "best_prior_range_low_in_sweep": best_range,
        "spotlight_causal_features": spotlight_features,
        "conservative_vs_aggressive_walkforward": wf_compare,
        "interpretation_ko": {
            "T5_range": "6/8 시가가 전일 레인지 하단(~0.03)이면 갭 없이도 bull→bear 가능",
            "T6_vol_gated": "고변동 국면에서만 composite — 불필요한 갭 트리거 감소 목적",
            "T3b_conservative": "overnight −2.5%로 T3 −2.0%보다 보수; OOS 비교로 과적합 완화",
        },
        "track_wall": "no_track_a_live_auto_merge",
    }

    assert_output_path_isolated(out_path.resolve())
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    t3b = next((t for t in tier_rows if t["tier_id"] == "T3b_composite_conservative"), {})
    t5 = next((t for t in tier_rows if t["tier_id"] == "T5_prior_range_low_open"), {})
    t6 = next((t for t in tier_rows if t["tier_id"] == "T6_vol_gated_composite_conservative"), {})
    return {
        "step": "causal_vol_range_proxy_ablation",
        "output": _rel(out_path),
        "composite_conservative_delta": t3b.get("delta_hit_rate"),
        "range_low_delta": t5.get("delta_hit_rate"),
        "vol_gated_delta": t6.get("delta_hit_rate"),
        "wf_conservative_test_delta": wf_compare.get("mean_test_delta_conservative"),
        "wf_conservative_minus_aggressive_pp": wf_compare.get("conservative_minus_aggressive_test_pp"),
        "spotlight_6_8_range": next(
            (s for s in t5.get("spotlight") or [] if s.get("date") == "2026-06-08"),
            None,
        ),
    }


def _chronological_holdout_split(
    rows: list[dict[str, Any]], train_ratio: float
) -> tuple[set[str], set[str]]:
    dates = sorted({str(r.get("eval_date") or "")[:10] for r in rows if r.get("eval_date")})
    if len(dates) < 10:
        return set(), set()
    cut = max(1, int(len(dates) * float(train_ratio)))
    if cut >= len(dates):
        cut = len(dates) - 1
    return set(dates[:cut]), set(dates[cut:])


def _build_fold_overlay_day_audit(
    *,
    rows_in: list[dict[str, Any]],
    wf_folds: list[dict[str, Any]],
    n_folds: int,
    overlay: str,
    prior_map: dict[str, float],
    overnight_map: dict[str, float],
    mild: float,
    guard: float,
    range_map: dict[str, float],
    vol_map: dict[str, float] | None = None,
    vol_thr: float | None = None,
    ovn_conservative: float | None = None,
    range_threshold_key: str = "prior_range_low_threshold",
) -> list[dict[str, Any]]:
    """Per-fold test-day overlay modification audit [HYPO]."""
    slices = _chronological_walkforward_slices(rows_in, n_folds)
    slice_by_fold = {i: (train_d, test_d) for i, (train_d, test_d) in enumerate(slices)}
    audit_folds: list[dict[str, Any]] = []
    for fold_row in wf_folds:
        fold_idx = int(fold_row.get("fold") or 0)
        slice_pair = slice_by_fold.get(fold_idx)
        if not slice_pair:
            continue
        _train_d, test_d = slice_pair
        sel_thr = float((fold_row.get("selected_on_train") or {}).get(range_threshold_key) or 0.15)
        test_rows = _filter_rows_by_dates(rows_in, test_d)
        _, _, te_delta, overlaid = _overlay_delta_on_rows(
            test_rows,
            overlay=overlay,
            prior_map=prior_map,
            overnight_map=overnight_map,
            intraday_map=None,
            prior_return_threshold=mild,
            rebound_guard_threshold=guard,
            session_open_composite_overnight_threshold=ovn_conservative,
            realized_vol_map=vol_map,
            vol_regime_threshold=vol_thr,
            range_position_map=range_map,
            prior_range_low_threshold=sel_thr,
        )
        base_by = {str(r.get("eval_date") or "")[:10]: r for r in test_rows}
        ov_by = {str(r.get("eval_date") or "")[:10]: r for r in overlaid}
        modified_days: list[dict[str, Any]] = []
        wins = losses = 0
        for dk in sorted(test_d):
            base_r = base_by.get(dk)
            ov_r = ov_by.get(dk)
            if not base_r or not ov_r:
                continue
            base_pred = str(base_r.get("predicted_direction") or "").strip().lower()
            after_pred = str(ov_r.get("predicted_direction") or "").strip().lower()
            if base_pred == after_pred:
                continue
            actual = str(base_r.get("actual_direction") or "").strip().lower()
            base_hit = base_pred == actual and base_pred in ("bull", "bear")
            after_hit = after_pred == actual and after_pred in ("bull", "bear")
            if after_hit and not base_hit:
                wins += 1
            elif base_hit and not after_hit:
                losses += 1
            modified_days.append(
                {
                    "date": dk,
                    "baseline_predicted": base_pred,
                    "after_overlay_predicted": after_pred,
                    "actual_direction": actual,
                    "baseline_hit": base_hit,
                    "after_overlay_hit": after_hit,
                    "overlay_rule": ov_r.get("overlay_rule"),
                    "overlay_triggers": ov_r.get("overlay_triggers"),
                }
            )
        audit_folds.append(
            {
                "fold": fold_row.get("fold"),
                "test_delta_hit_rate": te_delta,
                "n_test_dates": len(test_d),
                "n_modified": len(modified_days),
                "hit_improvements": wins,
                "hit_regressions": losses,
                "modified_days": modified_days,
            }
        )
    return audit_folds


def run_causal_proxy_ensemble_holdout_ablation_sidecar(
    *,
    recipe: dict[str, Any],
    panel_csv: Path,
    kospi_csv: Path,
    date_from: str,
    date_to: str,
    spotlight_dates: list[str],
    out_path: Path,
    dry_run: bool,
) -> dict[str, Any]:
    """T5+T3b OR ensemble + range threshold holdout / blocked WF [HYPO]."""
    ablation = (
        recipe.get("causal_proxy_ensemble_holdout_ablation")
        if isinstance(recipe.get("causal_proxy_ensemble_holdout_ablation"), dict)
        else {}
    )
    n_folds = int(ablation.get("n_walkforward_folds") or 4)
    train_ratio = float(ablation.get("holdout_train_ratio") or 0.8)
    mild = float((ablation.get("shared_rebound_guard") or {}).get("mild") or -0.048)
    guard = float((ablation.get("shared_rebound_guard") or {}).get("guard") or -0.07)
    ovn_conservative = float(ablation.get("composite_overnight_conservative") or -0.025)
    range_sweep = list(ablation.get("prior_range_low_threshold_sweep") or [0.10, 0.15, 0.20, 0.25])
    range_rec = float(ablation.get("prior_range_low_threshold_recommended") or 0.15)
    vol_thr = float(ablation.get("vol_regime_threshold_recommended") or 0.03)
    variant_key = str(ablation.get("multilens_variant") or "operational_baseline")

    if dry_run:
        return {
            "step": "causal_proxy_ensemble_holdout_ablation",
            "skipped": True,
            "output": _rel(out_path),
        }

    if not panel_csv.is_file() or not kospi_csv.is_file():
        return {
            "step": "causal_proxy_ensemble_holdout_ablation",
            "skipped": True,
            "reason": "missing panel or kospi",
        }

    from scripts.run_prophecy_restoration_spike import (
        _eval_directional_hit,
        _overnight_return_by_eval_date,
        _prior_completed_daily_return_by_eval_date,
        _prior_range_position_by_eval_date,
        _realized_vol_5d_by_eval_date,
    )

    rows_in = build_multilens_eval_rows(
        recipe=recipe,
        panel_csv=panel_csv,
        kospi_csv=kospi_csv,
        date_from=date_from,
        date_to=date_to,
        variant_key=variant_key,
    )
    if not rows_in:
        return {
            "step": "causal_proxy_ensemble_holdout_ablation",
            "skipped": True,
            "reason": "no multilens eval rows",
        }

    prior_map = _prior_completed_daily_return_by_eval_date(kospi_csv)
    overnight_map = _overnight_return_by_eval_date(kospi_csv)
    range_map = _prior_range_position_by_eval_date(kospi_csv)
    vol_map = _realized_vol_5d_by_eval_date(kospi_csv)
    base_rate, base_n, _ = _eval_directional_hit(rows_in)

    def _spotlight(overlaid: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return _spotlight_for_overlay(
            rows_in=rows_in,
            overlaid=overlaid,
            prior_map=prior_map,
            overnight_map=overnight_map,
            intraday_drawdown_map=None,
            spotlight_dates=spotlight_dates,
            range_position_map=range_map,
            realized_vol_map=vol_map,
        )

    tier_specs = [
        {
            "tier_id": "T5_prior_range_low",
            "overlay": "prior_range_low_open_bull_to_bear_rebound_guard_v0",
            "prior_range_low_threshold": range_rec,
        },
        {
            "tier_id": "T3b_composite_conservative",
            "overlay": "session_open_composite_bull_to_bear_rebound_guard_v0",
            "session_open_composite_overnight_threshold": ovn_conservative,
        },
        {
            "tier_id": "T7_range_or_composite_ensemble",
            "overlay": "range_or_composite_conservative_bull_to_bear_rebound_guard_v0",
            "prior_range_low_threshold": range_rec,
            "session_open_composite_overnight_threshold": ovn_conservative,
        },
        {
            "tier_id": "T6_vol_gated_composite_conservative",
            "overlay": "vol_gated_session_open_composite_bull_to_bear_rebound_guard_v0",
            "session_open_composite_overnight_threshold": ovn_conservative,
            "vol_regime_threshold": vol_thr,
        },
        {
            "tier_id": "T8_triple_causal_proxy_ensemble",
            "overlay": "range_or_composite_or_vol_gated_conservative_bull_to_bear_rebound_guard_v0",
            "prior_range_low_threshold": range_rec,
            "session_open_composite_overnight_threshold": ovn_conservative,
            "vol_regime_threshold": vol_thr,
        },
    ]

    tier_rows: list[dict[str, Any]] = []
    for spec in tier_specs:
        br, ov, delta, overlaid = _overlay_delta_on_rows(
            rows_in,
            overlay=str(spec["overlay"]),
            prior_map=prior_map,
            overnight_map=overnight_map,
            intraday_map=None,
            prior_return_threshold=mild,
            rebound_guard_threshold=guard,
            session_open_composite_overnight_threshold=spec.get("session_open_composite_overnight_threshold"),
            realized_vol_map=vol_map if "vol" in str(spec["overlay"]) else None,
            vol_regime_threshold=spec.get("vol_regime_threshold"),
            range_position_map=range_map,
            prior_range_low_threshold=spec.get("prior_range_low_threshold"),
        )
        tier_rows.append(
            {
                **spec,
                "causal_at_open": True,
                "baseline_hit_rate": br,
                "after_overlay_hit_rate": ov,
                "delta_hit_rate": delta,
                "n_evaluated": base_n,
                "spotlight": _spotlight(overlaid),
            }
        )

    train_dates, holdout_dates = _chronological_holdout_split(rows_in, train_ratio)
    train_rows = _filter_rows_by_dates(rows_in, train_dates)
    holdout_rows = _filter_rows_by_dates(rows_in, holdout_dates)

    best_range_train: dict[str, Any] | None = None
    for thr in range_sweep:
        thr_f = float(thr)
        _, _, train_delta, _ = _overlay_delta_on_rows(
            train_rows,
            overlay="prior_range_low_open_bull_to_bear_rebound_guard_v0",
            prior_map=prior_map,
            overnight_map=overnight_map,
            intraday_map=None,
            prior_return_threshold=mild,
            rebound_guard_threshold=guard,
            range_position_map=range_map,
            prior_range_low_threshold=thr_f,
        )
        cand = {"prior_range_low_threshold": thr_f, "train_delta_hit_rate": train_delta}
        if train_delta is not None and (
            best_range_train is None or train_delta > best_range_train.get("train_delta_hit_rate", -999)
        ):
            best_range_train = cand

    holdout_eval: dict[str, Any] = {}
    if best_range_train and holdout_rows:
        sel_thr = float(best_range_train["prior_range_low_threshold"])
        for label, overlay, extra in (
            (
                "T5_range_holdout",
                "prior_range_low_open_bull_to_bear_rebound_guard_v0",
                {"prior_range_low_threshold": sel_thr},
            ),
            (
                "T3b_composite_holdout",
                "session_open_composite_bull_to_bear_rebound_guard_v0",
                {"session_open_composite_overnight_threshold": ovn_conservative},
            ),
            (
                "T7_ensemble_holdout",
                "range_or_composite_conservative_bull_to_bear_rebound_guard_v0",
                {
                    "prior_range_low_threshold": sel_thr,
                    "session_open_composite_overnight_threshold": ovn_conservative,
                },
            ),
            (
                "T8_triple_ensemble_holdout",
                "range_or_composite_or_vol_gated_conservative_bull_to_bear_rebound_guard_v0",
                {
                    "prior_range_low_threshold": sel_thr,
                    "session_open_composite_overnight_threshold": ovn_conservative,
                    "realized_vol_map": vol_map,
                    "vol_regime_threshold": vol_thr,
                },
            ),
        ):
            vol_extra = extra.pop("realized_vol_map", None)
            vol_reg = extra.pop("vol_regime_threshold", None)
            _, _, hold_delta, _ = _overlay_delta_on_rows(
                holdout_rows,
                overlay=overlay,
                prior_map=prior_map,
                overnight_map=overnight_map,
                intraday_map=None,
                prior_return_threshold=mild,
                rebound_guard_threshold=guard,
                range_position_map=range_map,
                realized_vol_map=vol_extra,
                vol_regime_threshold=vol_reg,
                session_open_composite_overnight_threshold=extra.get(
                    "session_open_composite_overnight_threshold"
                ),
                prior_range_low_threshold=extra.get("prior_range_low_threshold"),
            )
            row_out: dict[str, Any] = {"holdout_delta_hit_rate": hold_delta, **extra}
            if vol_reg is not None:
                row_out["vol_regime_threshold"] = vol_reg
            holdout_eval[label] = row_out

    wf_slices = _chronological_walkforward_slices(rows_in, n_folds)
    wf_range_folds: list[dict[str, Any]] = []
    wf_test_deltas: list[float] = []
    for fold_idx, (train_d, test_d) in enumerate(wf_slices):
        tr_rows = _filter_rows_by_dates(rows_in, train_d)
        te_rows = _filter_rows_by_dates(rows_in, test_d)
        best_fold: dict[str, Any] | None = None
        for thr in range_sweep:
            thr_f = float(thr)
            _, _, tr_delta, _ = _overlay_delta_on_rows(
                tr_rows,
                overlay="prior_range_low_open_bull_to_bear_rebound_guard_v0",
                prior_map=prior_map,
                overnight_map=overnight_map,
                intraday_map=None,
                prior_return_threshold=mild,
                rebound_guard_threshold=guard,
                range_position_map=range_map,
                prior_range_low_threshold=thr_f,
            )
            if tr_delta is None:
                continue
            cand = {"prior_range_low_threshold": thr_f, "train_delta_hit_rate": tr_delta}
            if best_fold is None or tr_delta > best_fold.get("train_delta_hit_rate", -999):
                best_fold = cand
        if best_fold is None:
            continue
        _, _, te_delta, _ = _overlay_delta_on_rows(
            te_rows,
            overlay="prior_range_low_open_bull_to_bear_rebound_guard_v0",
            prior_map=prior_map,
            overnight_map=overnight_map,
            intraday_map=None,
            prior_return_threshold=mild,
            rebound_guard_threshold=guard,
            range_position_map=range_map,
            prior_range_low_threshold=float(best_fold["prior_range_low_threshold"]),
        )
        wf_range_folds.append(
            {
                "fold": fold_idx,
                "selected_on_train": best_fold,
                "test_delta_hit_rate": te_delta,
            }
        )
        if te_delta is not None:
            wf_test_deltas.append(float(te_delta))

    fold_day_audit = _build_fold_overlay_day_audit(
        rows_in=rows_in,
        wf_folds=wf_range_folds,
        n_folds=n_folds,
        overlay="prior_range_low_open_bull_to_bear_rebound_guard_v0",
        prior_map=prior_map,
        overnight_map=overnight_map,
        mild=mild,
        guard=guard,
        range_map=range_map,
    )

    t7 = next((t for t in tier_rows if t["tier_id"] == "T7_range_or_composite_ensemble"), {})
    t8 = next((t for t in tier_rows if t["tier_id"] == "T8_triple_causal_proxy_ensemble"), {})
    t8_minus_t7_pp = (
        round(float(t8.get("delta_hit_rate")) - float(t7.get("delta_hit_rate")), 6)
        if t8.get("delta_hit_rate") is not None and t7.get("delta_hit_rate") is not None
        else None
    )
    payload: dict[str, Any] = {
        "schema": "max_hypo_causal_proxy_ensemble_holdout_ablation_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "hypothesis_tag": "[MAX_HYPO][HYPO]",
        "multilens_baseline_hit_rate": base_rate,
        "full_window_tiers": tier_rows,
        "holdout_split": {
            "train_ratio": train_ratio,
            "n_train_dates": len(train_dates),
            "n_holdout_dates": len(holdout_dates),
            "selected_range_threshold_on_train": best_range_train,
            "holdout_eval": holdout_eval,
            "note_ko": "train에서 range threshold grid 최적 → holdout(맨 뒤 20%)만 평가",
        },
        "range_threshold_blocked_walkforward": {
            "n_folds_effective": len(wf_range_folds),
            "mean_test_delta_hit_rate": round(sum(wf_test_deltas) / len(wf_test_deltas), 6)
            if wf_test_deltas
            else None,
            "folds": wf_range_folds,
        },
        "holdout_fold_day_audit": {
            "overlay": "prior_range_low_open_bull_to_bear_rebound_guard_v0",
            "note_ko": "T5 range WF fold별 test 구간 수정 일자·적중 개선/악화",
            "folds": fold_day_audit,
        },
        "interpretation_ko": {
            "T7_ensemble": "range OR composite conservative — 둘 중 하나만 걸려도 bear; 6/8·6/9 스포트라이트 유지 목적",
            "T8_triple": "T5∨T3b∨vol-gated composite; vol-gated ⊆ composite 이면 T7과 동일 Δ 가능",
            "T8_minus_T7_pp": t8_minus_t7_pp,
            "holdout": "holdout Δ가 full-window Δ보다 낮으면 과적합·창 의존 신호",
            "range_wf": "fold별 range threshold 재선택 OOS 안정성",
            "fold_day_audit": "test_delta 낮은 fold의 regression 일자 확인",
        },
        "track_wall": "no_track_a_live_auto_merge",
    }

    assert_output_path_isolated(out_path.resolve())
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "step": "causal_proxy_ensemble_holdout_ablation",
        "output": _rel(out_path),
        "ensemble_delta": t7.get("delta_hit_rate"),
        "range_delta": next(
            (t.get("delta_hit_rate") for t in tier_rows if t["tier_id"] == "T5_prior_range_low"),
            None,
        ),
        "holdout_ensemble_delta": (holdout_eval.get("T7_ensemble_holdout") or {}).get("holdout_delta_hit_rate"),
        "triple_ensemble_delta": t8.get("delta_hit_rate"),
        "triple_minus_t7_pp": t8_minus_t7_pp,
        "holdout_triple_ensemble_delta": (holdout_eval.get("T8_triple_ensemble_holdout") or {}).get(
            "holdout_delta_hit_rate"
        ),
        "range_wf_mean_test_delta": payload["range_threshold_blocked_walkforward"].get("mean_test_delta_hit_rate"),
        "spotlight_6_8_ensemble": next(
            (s for s in t7.get("spotlight") or [] if s.get("date") == "2026-06-08"),
            None,
        ),
        "spotlight_6_8_triple": next(
            (s for s in t8.get("spotlight") or [] if s.get("date") == "2026-06-08"),
            None,
        ),
    }


def _wf_range_test_deltas_by_fold(
    rows_in: list[dict[str, Any]],
    *,
    n_folds: int,
    range_sweep: list[float],
    overlay: str,
    prior_map: dict[str, float],
    overnight_map: dict[str, float],
    range_map: dict[str, float],
    mild: float,
    guard: float,
    range_rec: float,
    overnight_skip: float | None,
) -> dict[int, float | None]:
    wf_slices = _chronological_walkforward_slices(rows_in, n_folds)
    out: dict[int, float | None] = {}
    for fold_idx, (train_d, test_d) in enumerate(wf_slices):
        tr_rows = _filter_rows_by_dates(rows_in, train_d)
        te_rows = _filter_rows_by_dates(rows_in, test_d)
        best_thr = range_rec
        best_train: float | None = None
        for thr in range_sweep:
            _, _, tr_delta, _ = _overlay_delta_on_rows(
                tr_rows,
                overlay=overlay,
                prior_map=prior_map,
                overnight_map=overnight_map,
                intraday_map=None,
                prior_return_threshold=mild,
                rebound_guard_threshold=guard,
                range_position_map=range_map,
                prior_range_low_threshold=float(thr),
                overnight_gap_rebound_skip_threshold=overnight_skip,
            )
            if tr_delta is not None and (best_train is None or tr_delta > best_train):
                best_train = tr_delta
                best_thr = float(thr)
        _, _, te_delta, _ = _overlay_delta_on_rows(
            te_rows,
            overlay=overlay,
            prior_map=prior_map,
            overnight_map=overnight_map,
            intraday_map=None,
            prior_return_threshold=mild,
            rebound_guard_threshold=guard,
            range_position_map=range_map,
            prior_range_low_threshold=best_thr,
            overnight_gap_rebound_skip_threshold=overnight_skip,
        )
        out[fold_idx] = te_delta
    return out


def _regression_audit_score(
    rows_in: list[dict[str, Any]],
    overlaid: list[dict[str, Any]],
    audit_dates: list[str],
) -> dict[str, Any]:
    base_by = {str(r.get("eval_date") or "")[:10]: r for r in rows_in}
    ov_by = {str(r.get("eval_date") or "")[:10]: r for r in overlaid}
    remaining = 0
    per_date: list[dict[str, Any]] = []
    for dk in audit_dates:
        base_r = base_by.get(dk)
        ov_r = ov_by.get(dk)
        if not base_r or not ov_r:
            continue
        base_pred = str(base_r.get("predicted_direction") or "").strip().lower()
        after_pred = str(ov_r.get("predicted_direction") or "").strip().lower()
        actual = str(base_r.get("actual_direction") or "").strip().lower()
        was_regression = base_pred == actual and after_pred != actual
        if was_regression:
            remaining += 1
        per_date.append(
            {
                "date": dk,
                "baseline_predicted": base_pred,
                "after_overlay_predicted": after_pred,
                "actual_direction": actual,
                "was_regression_baseline": was_regression,
                "after_overlay_hit": after_pred == actual,
            }
        )
    return {
        "audit_dates": audit_dates,
        "regressions_remaining": remaining,
        "per_date": per_date,
    }


def _regression_fix_vs_reference(
    rows_in: list[dict[str, Any]],
    overlaid_candidate: list[dict[str, Any]],
    overlaid_reference: list[dict[str, Any]],
    audit_dates: list[str],
) -> dict[str, Any]:
    base_by = {str(r.get("eval_date") or "")[:10]: r for r in rows_in}
    ref_by = {str(r.get("eval_date") or "")[:10]: r for r in overlaid_reference}
    cand_by = {str(r.get("eval_date") or "")[:10]: r for r in overlaid_candidate}
    fixed = remaining = 0
    per_date: list[dict[str, Any]] = []
    for dk in audit_dates:
        base_r = base_by.get(dk)
        ref_r = ref_by.get(dk)
        cand_r = cand_by.get(dk)
        if not base_r or not ref_r or not cand_r:
            continue
        base_pred = str(base_r.get("predicted_direction") or "").strip().lower()
        actual = str(base_r.get("actual_direction") or "").strip().lower()
        ref_pred = str(ref_r.get("predicted_direction") or "").strip().lower()
        cand_pred = str(cand_r.get("predicted_direction") or "").strip().lower()
        ref_regression = base_pred == actual and ref_pred != actual
        cand_ok = cand_pred == actual
        if ref_regression and cand_ok:
            fixed += 1
        elif ref_regression and not cand_ok:
            remaining += 1
        per_date.append(
            {
                "date": dk,
                "baseline_predicted": base_pred,
                "reference_overlay_predicted": ref_pred,
                "candidate_overlay_predicted": cand_pred,
                "actual_direction": actual,
                "reference_was_regression": ref_regression,
                "candidate_hit": cand_ok,
            }
        )
    return {
        "audit_dates": audit_dates,
        "regressions_fixed_vs_reference": fixed,
        "regressions_remaining_vs_reference": remaining,
        "per_date": per_date,
    }


def _write_range_rebound_refinement_md(payload: dict[str, Any], md_path: Path) -> None:
    rec = payload.get("recommended") or {}
    lines = [
        "# MAX_HYPO range rebound refinement v1",
        "",
        "`[MAX_HYPO][HYPO]` · `research_only` · Track A / live auto-merge 없음.",
        "",
        f"- generated: {payload.get('generated_at_utc')}",
        f"- baseline hit rate: {payload.get('multilens_baseline_hit_rate')}",
        "",
        "## Recommended",
        "",
        f"- rebound_guard: **{rec.get('rebound_guard_threshold')}**",
        f"- overnight_gap_rebound_skip: **{rec.get('overnight_gap_rebound_skip_threshold')}**",
        f"- full-window Δ: **{rec.get('full_window_delta_hit_rate')}**",
        f"- WF mean test Δ: **{rec.get('wf_mean_test_delta_hit_rate')}**",
        f"- WF fold-1 test Δ: **{rec.get('wf_fold_1_test_delta_hit_rate')}**",
        f"- fold-1 regressions remaining: **{rec.get('fold1_regressions_remaining')}**",
        "",
        "## Spotlight",
        "",
    ]
    for row in payload.get("spotlight_recommended") or []:
        lines.append(
            f"- {row.get('date')}: baseline={row.get('baseline_predicted')} "
            f"after={row.get('after_overlay_predicted')} actual={row.get('actual_direction')} "
            f"hit={row.get('after_overlay_hit')}"
        )
    lines.extend(["", "## Grid top-3 (spotlight-safe)", ""])
    for row in (payload.get("grid_ranked_spotlight_safe") or [])[:3]:
        lines.append(
            f"- guard={row.get('rebound_guard_threshold')} skip={row.get('overnight_gap_rebound_skip_threshold')} "
            f"Δ={row.get('full_window_delta_hit_rate')} fold1={row.get('wf_fold_1_test_delta_hit_rate')}"
        )
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_range_rebound_guard_refinement_sidecar(
    *,
    recipe: dict[str, Any],
    panel_csv: Path,
    kospi_csv: Path,
    date_from: str,
    date_to: str,
    spotlight_dates: list[str],
    out_path: Path,
    md_path: Path,
    dry_run: bool,
) -> dict[str, Any]:
    """Guard + overnight gap-up skip sweep on T5 range overlay [HYPO]."""
    ablation = (
        recipe.get("range_rebound_guard_refinement")
        if isinstance(recipe.get("range_rebound_guard_refinement"), dict)
        else {}
    )
    n_folds = int(ablation.get("n_walkforward_folds") or 4)
    mild = float((ablation.get("shared_rebound_guard") or {}).get("mild") or -0.048)
    guard_sweep = list(ablation.get("rebound_guard_threshold_sweep") or [-0.065, -0.07, -0.075, -0.08])
    overnight_skip_sweep = ablation.get("overnight_gap_rebound_skip_sweep")
    if overnight_skip_sweep is None:
        overnight_skip_sweep = [None, 0.0, 0.005]
    range_rec = float(ablation.get("prior_range_low_threshold_recommended") or 0.15)
    range_sweep = list(ablation.get("prior_range_low_threshold_sweep") or [0.10, 0.15, 0.20, 0.25])
    audit_dates = list(ablation.get("fold_regression_audit_dates") or ["2026-01-09", "2026-01-21", "2026-01-27"])
    variant_key = str(ablation.get("multilens_variant") or "operational_baseline")
    overlay = "prior_range_low_open_bull_to_bear_rebound_guard_v0"

    if dry_run:
        return {
            "step": "range_rebound_guard_refinement",
            "skipped": True,
            "output": _rel(out_path),
        }

    if not panel_csv.is_file() or not kospi_csv.is_file():
        return {
            "step": "range_rebound_guard_refinement",
            "skipped": True,
            "reason": "missing panel or kospi",
        }

    rows_in = build_multilens_eval_rows(
        recipe=recipe,
        panel_csv=panel_csv,
        kospi_csv=kospi_csv,
        date_from=date_from,
        date_to=date_to,
        variant_key=variant_key,
    )
    if not rows_in:
        return {"step": "range_rebound_guard_refinement", "skipped": True, "reason": "no rows"}

    from scripts.run_prophecy_restoration_spike import (
        _eval_directional_hit,
        _overnight_return_by_eval_date,
        _prior_completed_daily_return_by_eval_date,
        _prior_range_position_by_eval_date,
    )

    prior_map = _prior_completed_daily_return_by_eval_date(kospi_csv)
    overnight_map = _overnight_return_by_eval_date(kospi_csv)
    range_map = _prior_range_position_by_eval_date(kospi_csv)
    base_rate, base_n, _ = _eval_directional_hit(rows_in)

    grid_rows: list[dict[str, Any]] = []
    for guard in guard_sweep:
        guard_f = float(guard)
        for skip_raw in overnight_skip_sweep:
            skip_f = None if skip_raw is None else float(skip_raw)
            br, ov, delta, overlaid = _overlay_delta_on_rows(
                rows_in,
                overlay=overlay,
                prior_map=prior_map,
                overnight_map=overnight_map,
                intraday_map=None,
                prior_return_threshold=mild,
                rebound_guard_threshold=guard_f,
                range_position_map=range_map,
                prior_range_low_threshold=range_rec,
                overnight_gap_rebound_skip_threshold=skip_f,
            )
            fold_deltas = _wf_range_test_deltas_by_fold(
                rows_in,
                n_folds=n_folds,
                range_sweep=range_sweep,
                overlay=overlay,
                prior_map=prior_map,
                overnight_map=overnight_map,
                range_map=range_map,
                mild=mild,
                guard=guard_f,
                range_rec=range_rec,
                overnight_skip=skip_f,
            )
            wf_vals = [v for v in fold_deltas.values() if v is not None]
            wf_mean = round(sum(wf_vals) / len(wf_vals), 6) if wf_vals else None
            spotlight = _spotlight_for_overlay(
                rows_in=rows_in,
                overlaid=overlaid,
                prior_map=prior_map,
                overnight_map=overnight_map,
                intraday_drawdown_map=None,
                spotlight_dates=spotlight_dates,
                range_position_map=range_map,
            )
            spot_ok = True
            for dk in spotlight_dates:
                sp = next((s for s in spotlight if s.get("date") == dk), None)
                if not sp or sp.get("status"):
                    spot_ok = False
                    break
                actual = str(sp.get("actual_direction") or "").lower()
                after = str(sp.get("after_overlay_predicted") or "").lower()
                if after != actual:
                    spot_ok = False
                    break
            reg = _regression_audit_score(rows_in, overlaid, audit_dates)
            grid_rows.append(
                {
                    "rebound_guard_threshold": guard_f,
                    "overnight_gap_rebound_skip_threshold": skip_f,
                    "baseline_hit_rate": br,
                    "after_overlay_hit_rate": ov,
                    "full_window_delta_hit_rate": delta,
                    "wf_mean_test_delta_hit_rate": wf_mean,
                    "wf_fold_1_test_delta_hit_rate": fold_deltas.get(1),
                    "wf_fold_deltas": {str(k): v for k, v in fold_deltas.items()},
                        "spotlight_safe": spot_ok,
                        "fold1_regressions_remaining": reg["regressions_remaining"],
                    "regression_audit": reg,
                    "spotlight": spotlight,
                }
            )

    safe_rows = [r for r in grid_rows if r.get("spotlight_safe")]
    rank_pool = safe_rows if safe_rows else grid_rows

    def _rank_key(row: dict[str, Any]) -> tuple:
        f1 = row.get("wf_fold_1_test_delta_hit_rate")
        wf = row.get("wf_mean_test_delta_hit_rate")
        delta = row.get("full_window_delta_hit_rate")
        remaining = row.get("fold1_regressions_remaining") or 0
        return (
            -remaining,
            f1 if f1 is not None else -999.0,
            wf if wf is not None else -999.0,
            delta if delta is not None else -999.0,
        )

    ranked = sorted(rank_pool, key=_rank_key, reverse=True)
    recommended = ranked[0] if ranked else {}
    baseline_block = next(
        (
            r
            for r in grid_rows
            if r.get("rebound_guard_threshold") == -0.07 and r.get("overnight_gap_rebound_skip_threshold") is None
        ),
        None,
    )

    payload: dict[str, Any] = {
        "schema": "max_hypo_range_rebound_guard_refinement_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "hypothesis_tag": "[MAX_HYPO][HYPO]",
        "multilens_baseline_hit_rate": base_rate,
        "n_evaluated": base_n,
        "overlay": overlay,
        "prior_range_low_threshold": range_rec,
        "baseline_guard_no_overnight_skip": baseline_block,
        "grid": grid_rows,
        "grid_ranked_spotlight_safe": ranked[:5],
        "recommended": recommended,
        "recommended_vs_baseline": {
            "fold1_test_delta_pp": (
                round(
                    float(recommended.get("wf_fold_1_test_delta_hit_rate") or 0)
                    - float((baseline_block or {}).get("wf_fold_1_test_delta_hit_rate") or 0),
                    6,
                )
                if recommended and baseline_block
                else None
            ),
            "full_window_delta_pp": (
                round(
                    float(recommended.get("full_window_delta_hit_rate") or 0)
                    - float((baseline_block or {}).get("full_window_delta_hit_rate") or 0),
                    6,
                )
                if recommended and baseline_block
                else None
            ),
        },
        "spotlight_recommended": recommended.get("spotlight"),
        "interpretation_ko": {
            "overnight_skip": "갭 상승(시가 rebound) 시 range-low bear 스킵 — fold1 V-rebound 오탐 완화 목적",
            "guard_sweep": "extreme prior rebound guard 세밀화; 6/9 스포트라이트 유지 필수",
        },
        "track_wall": "no_track_a_live_auto_merge",
    }

    assert_output_path_isolated(out_path.resolve())
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _write_range_rebound_refinement_md(payload, md_path)

    return {
        "step": "range_rebound_guard_refinement",
        "output": _rel(out_path),
        "md_output": _rel(md_path),
        "recommended_guard": recommended.get("rebound_guard_threshold"),
        "recommended_overnight_skip": recommended.get("overnight_gap_rebound_skip_threshold"),
        "recommended_delta": recommended.get("full_window_delta_hit_rate"),
        "wf_fold_1_test_delta": recommended.get("wf_fold_1_test_delta_hit_rate"),
        "fold1_regressions_remaining": recommended.get("fold1_regressions_remaining"),
        "spotlight_safe": recommended.get("spotlight_safe"),
    }


def _write_prior_mild_range_conjunction_md(payload: dict[str, Any], md_path: Path) -> None:
    rec = payload.get("recommended") or {}
    base = payload.get("baseline_t5_range_only") or {}
    lines = [
        "# MAX_HYPO prior-mild AND range-low conjunction v1",
        "",
        "`[MAX_HYPO][HYPO]` · `research_only` · Track A / live auto-merge 없음.",
        "",
        f"- generated: {payload.get('generated_at_utc')}",
        "",
        "## T5 range-only (baseline)",
        "",
        f"- full Δ: {base.get('full_window_delta_hit_rate')} · fold-1 test Δ: {base.get('wf_fold_1_test_delta_hit_rate')}",
        f"- fold1 regressions remaining: {base.get('fold1_regressions_remaining')}",
        "",
        "## T9 mild∧range (recommended)",
        "",
        f"- mild threshold: {rec.get('prior_mild_threshold')}",
        f"- rebound guard: {rec.get('rebound_guard_threshold')}",
        f"- full Δ: **{rec.get('full_window_delta_hit_rate')}**",
        f"- WF fold-1 test Δ: **{rec.get('wf_fold_1_test_delta_hit_rate')}**",
        f"- fold1 regressions fixed vs T5: **{rec.get('regressions_fixed')}** · remaining vs T5: {rec.get('regressions_remaining_vs_t5')}",
        "",
        "## Spotlight",
        "",
    ]
    for row in payload.get("spotlight_recommended") or []:
        lines.append(
            f"- {row.get('date')}: after={row.get('after_overlay_predicted')} "
            f"actual={row.get('actual_direction')} hit={row.get('after_overlay_hit')}"
        )
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_prior_mild_range_conjunction_ablation_sidecar(
    *,
    recipe: dict[str, Any],
    panel_csv: Path,
    kospi_csv: Path,
    date_from: str,
    date_to: str,
    spotlight_dates: list[str],
    out_path: Path,
    md_path: Path,
    dry_run: bool,
) -> dict[str, Any]:
    """T5 range-only vs T9 prior-mild∧range-low conjunction [HYPO]."""
    ablation = (
        recipe.get("prior_mild_range_conjunction_ablation")
        if isinstance(recipe.get("prior_mild_range_conjunction_ablation"), dict)
        else {}
    )
    n_folds = int(ablation.get("n_walkforward_folds") or 4)
    guard = float(ablation.get("rebound_guard_threshold_recommended") or -0.075)
    mild_sweep = list(ablation.get("prior_mild_threshold_sweep") or [-0.04, -0.048, -0.055])
    range_rec = float(ablation.get("prior_range_low_threshold_recommended") or 0.15)
    range_sweep = list(ablation.get("prior_range_low_threshold_sweep") or [0.10, 0.15, 0.20, 0.25])
    audit_dates = list(ablation.get("fold_regression_audit_dates") or ["2026-01-09", "2026-01-21", "2026-01-27"])
    variant_key = str(ablation.get("multilens_variant") or "operational_baseline")
    overlay_or = "prior_range_low_open_bull_to_bear_rebound_guard_v0"
    overlay_and = "prior_mild_and_range_low_open_bull_to_bear_rebound_guard_v0"

    if dry_run:
        return {"step": "prior_mild_range_conjunction_ablation", "skipped": True, "output": _rel(out_path)}

    if not panel_csv.is_file() or not kospi_csv.is_file():
        return {
            "step": "prior_mild_range_conjunction_ablation",
            "skipped": True,
            "reason": "missing panel or kospi",
        }

    rows_in = build_multilens_eval_rows(
        recipe=recipe,
        panel_csv=panel_csv,
        kospi_csv=kospi_csv,
        date_from=date_from,
        date_to=date_to,
        variant_key=variant_key,
    )
    if not rows_in:
        return {"step": "prior_mild_range_conjunction_ablation", "skipped": True, "reason": "no rows"}

    from scripts.run_prophecy_restoration_spike import (
        _eval_directional_hit,
        _overnight_return_by_eval_date,
        _prior_completed_daily_return_by_eval_date,
        _prior_range_position_by_eval_date,
    )

    prior_map = _prior_completed_daily_return_by_eval_date(kospi_csv)
    overnight_map = _overnight_return_by_eval_date(kospi_csv)
    range_map = _prior_range_position_by_eval_date(kospi_csv)
    base_rate, base_n, _ = _eval_directional_hit(rows_in)

    mild_baseline = float(mild_sweep[1] if len(mild_sweep) > 1 else -0.048)
    _, _, _, overlaid_t5_ref = _overlay_delta_on_rows(
        rows_in,
        overlay=overlay_or,
        prior_map=prior_map,
        overnight_map=overnight_map,
        intraday_map=None,
        prior_return_threshold=mild_baseline,
        rebound_guard_threshold=guard,
        range_position_map=range_map,
        prior_range_low_threshold=range_rec,
    )

    def _eval_tier(overlay: str, mild: float) -> dict[str, Any]:
        br, ov, delta, overlaid = _overlay_delta_on_rows(
            rows_in,
            overlay=overlay,
            prior_map=prior_map,
            overnight_map=overnight_map,
            intraday_map=None,
            prior_return_threshold=mild,
            rebound_guard_threshold=guard,
            range_position_map=range_map,
            prior_range_low_threshold=range_rec,
        )
        fold_deltas = _wf_range_test_deltas_by_fold(
            rows_in,
            n_folds=n_folds,
            range_sweep=range_sweep,
            overlay=overlay,
            prior_map=prior_map,
            overnight_map=overnight_map,
            range_map=range_map,
            mild=mild,
            guard=guard,
            range_rec=range_rec,
            overnight_skip=None,
        )
        wf_vals = [v for v in fold_deltas.values() if v is not None]
        spotlight = _spotlight_for_overlay(
            rows_in=rows_in,
            overlaid=overlaid,
            prior_map=prior_map,
            overnight_map=overnight_map,
            intraday_drawdown_map=None,
            spotlight_dates=spotlight_dates,
            range_position_map=range_map,
        )
        spot_ok = all(
            str(next((s for s in spotlight if s.get("date") == dk), {}).get("after_overlay_predicted") or "")
            == str(next((s for s in spotlight if s.get("date") == dk), {}).get("actual_direction") or "")
            for dk in spotlight_dates
            if next((s for s in spotlight if s.get("date") == dk), None)
        )
        reg_self = _regression_audit_score(rows_in, overlaid, audit_dates)
        reg_vs_t5 = _regression_fix_vs_reference(rows_in, overlaid, overlaid_t5_ref, audit_dates)
        return {
            "overlay": overlay,
            "prior_mild_threshold": mild,
            "rebound_guard_threshold": guard,
            "prior_range_low_threshold": range_rec,
            "baseline_hit_rate": br,
            "after_overlay_hit_rate": ov,
            "full_window_delta_hit_rate": delta,
            "wf_mean_test_delta_hit_rate": round(sum(wf_vals) / len(wf_vals), 6) if wf_vals else None,
            "wf_fold_1_test_delta_hit_rate": fold_deltas.get(1),
            "wf_fold_deltas": {str(k): v for k, v in fold_deltas.items()},
            "spotlight_safe": spot_ok,
            "spotlight": spotlight,
            "regressions_remaining": reg_self.get("regressions_remaining"),
            "regressions_fixed": reg_vs_t5.get("regressions_fixed_vs_reference"),
            "regressions_remaining_vs_t5": reg_vs_t5.get("regressions_remaining_vs_reference"),
            "regression_audit_vs_t5": reg_vs_t5,
        }

    baseline_t5 = _eval_tier(overlay_or, mild_baseline)

    and_grid: list[dict[str, Any]] = []
    for mild in mild_sweep:
        row = _eval_tier(overlay_and, float(mild))
        row["tier_id"] = "T9_prior_mild_and_range_low"
        and_grid.append(row)

    safe_and = [r for r in and_grid if r.get("spotlight_safe")]
    rank_pool = safe_and if safe_and else and_grid

    def _rank_key(row: dict[str, Any]) -> tuple:
        return (
            row.get("regressions_fixed") or 0,
            -(row.get("regressions_remaining") or 99),
            row.get("wf_fold_1_test_delta_hit_rate") or -999.0,
            row.get("full_window_delta_hit_rate") or -999.0,
        )

    recommended = max(rank_pool, key=_rank_key) if rank_pool else {}

    payload: dict[str, Any] = {
        "schema": "max_hypo_prior_mild_range_conjunction_ablation_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "hypothesis_tag": "[MAX_HYPO][HYPO]",
        "multilens_baseline_hit_rate": base_rate,
        "n_evaluated": base_n,
        "baseline_t5_range_only": {**baseline_t5, "tier_id": "T5_prior_range_low_or"},
        "t9_mild_and_range_grid": and_grid,
        "recommended": recommended,
        "recommended_vs_t5": {
            "full_window_delta_pp": (
                round(
                    float(recommended.get("full_window_delta_hit_rate") or 0)
                    - float(baseline_t5.get("full_window_delta_hit_rate") or 0),
                    6,
                )
                if recommended
                else None
            ),
            "fold1_test_delta_pp": (
                round(
                    float(recommended.get("wf_fold_1_test_delta_hit_rate") or 0)
                    - float(baseline_t5.get("wf_fold_1_test_delta_hit_rate") or 0),
                    6,
                )
                if recommended
                else None
            ),
            "regressions_fixed": recommended.get("regressions_fixed"),
            "t5_regressions_remaining": baseline_t5.get("regressions_remaining"),
        },
        "spotlight_recommended": recommended.get("spotlight"),
        "regression_feature_audit": {
            "2026-01-09": {"prior_completed_pct": 0.029, "range_pos": 0.0267, "note": "range-only false positive"},
            "2026-01-21": {"prior_completed_pct": -0.386, "range_pos": 0.0},
            "2026-01-27": {"prior_completed_pct": -0.811, "range_pos": 0.0},
            "2026-06-08": {"prior_completed_pct": -5.542, "range_pos": 0.029, "note": "mild∧range target hit"},
        },
        "interpretation_ko": {
            "conjunction": "prior mild 없이 range만 낮은 V-rebound 오탐 차단; 6/8은 mild+range 동시 충족",
        },
        "track_wall": "no_track_a_live_auto_merge",
    }

    assert_output_path_isolated(out_path.resolve())
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _write_prior_mild_range_conjunction_md(payload, md_path)

    return {
        "step": "prior_mild_range_conjunction_ablation",
        "output": _rel(out_path),
        "md_output": _rel(md_path),
        "t5_delta": baseline_t5.get("full_window_delta_hit_rate"),
        "t9_recommended_delta": recommended.get("full_window_delta_hit_rate"),
        "t9_fold1_test_delta": recommended.get("wf_fold_1_test_delta_hit_rate"),
        "regressions_fixed": recommended.get("regressions_fixed"),
        "regressions_remaining_vs_t5": recommended.get("regressions_remaining_vs_t5"),
        "spotlight_safe": recommended.get("spotlight_safe"),
    }


def _write_t9_ensemble_holdout_md(payload: dict[str, Any], md_path: Path) -> None:
    rec = payload.get("recommended_t10") or {}
    t7 = payload.get("baseline_t7") or {}
    t10 = payload.get("recommended_t10") or {}
    t8 = payload.get("baseline_t8") or {}
    t11 = payload.get("recommended_t11") or {}
    cmp_ = payload.get("t10_vs_t7") or {}
    lines = [
        "# MAX_HYPO T9-ensemble (T10/T11) holdout v1",
        "",
        "`[MAX_HYPO][HYPO]` · `research_only` · Track A / live auto-merge 없음.",
        "",
        f"- generated: {payload.get('generated_at_utc')}",
        "",
        "## T7 range∨composite (legacy range leg)",
        "",
        f"- full Δ: {t7.get('delta_hit_rate')} · guard: {t7.get('rebound_guard_threshold')}",
        "",
        "## T10 mild∧range∨composite (recommended)",
        "",
        f"- mild: {rec.get('prior_mild_threshold')} · guard: {rec.get('rebound_guard_threshold')}",
        f"- full Δ: **{t10.get('delta_hit_rate')}** · vs T7: **{cmp_.get('full_window_delta_pp')} pp**",
        f"- holdout Δ: {cmp_.get('holdout_delta_pp')}",
        f"- fold1 regressions fixed vs T7: **{cmp_.get('regressions_fixed_vs_t7')}** · remaining: {cmp_.get('regressions_remaining_vs_t7')}",
        "",
        "## T8 vs T11 triple",
        "",
        f"- T8 Δ: {t8.get('delta_hit_rate')} · T11 Δ: {t11.get('delta_hit_rate')} · T11−T8: {payload.get('t11_minus_t8_pp')} pp",
        "",
        "## Spotlight (T10)",
        "",
    ]
    for sp in t10.get("spotlight") or []:
        lines.append(
            f"- {sp.get('date')}: after={sp.get('after_overlay_predicted')} "
            f"actual={sp.get('actual_direction')} hit={sp.get('after_overlay_hit')}"
        )
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_t9_ensemble_holdout_ablation_sidecar(
    *,
    recipe: dict[str, Any],
    panel_csv: Path,
    kospi_csv: Path,
    date_from: str,
    date_to: str,
    spotlight_dates: list[str],
    out_path: Path,
    md_path: Path,
    dry_run: bool,
) -> dict[str, Any]:
    """T10/T11 ensemble with T9 AND range leg vs T7/T8 + holdout [HYPO]."""
    ablation = (
        recipe.get("t9_ensemble_holdout_ablation")
        if isinstance(recipe.get("t9_ensemble_holdout_ablation"), dict)
        else {}
    )
    train_ratio = float(ablation.get("holdout_train_ratio") or 0.8)
    guard = float(ablation.get("rebound_guard_threshold_recommended") or -0.075)
    mild_t9 = float(ablation.get("prior_mild_threshold_recommended") or -0.04)
    mild_legacy = float(ablation.get("composite_mild_threshold_legacy") or -0.048)
    ovn_conservative = float(ablation.get("composite_overnight_conservative") or -0.025)
    range_rec = float(ablation.get("prior_range_low_threshold_recommended") or 0.15)
    range_sweep = list(ablation.get("prior_range_low_threshold_sweep") or [0.10, 0.15, 0.20, 0.25])
    vol_thr = float(ablation.get("vol_regime_threshold_recommended") or 0.03)
    audit_dates = list(ablation.get("fold_regression_audit_dates") or ["2026-01-09", "2026-01-21", "2026-01-27"])
    variant_key = str(ablation.get("multilens_variant") or "operational_baseline")

    if dry_run:
        return {"step": "t9_ensemble_holdout_ablation", "skipped": True, "output": _rel(out_path)}

    if not panel_csv.is_file() or not kospi_csv.is_file():
        return {"step": "t9_ensemble_holdout_ablation", "skipped": True, "reason": "missing panel or kospi"}

    from scripts.run_prophecy_restoration_spike import (
        _eval_directional_hit,
        _overnight_return_by_eval_date,
        _prior_completed_daily_return_by_eval_date,
        _prior_range_position_by_eval_date,
        _realized_vol_5d_by_eval_date,
    )

    rows_in = build_multilens_eval_rows(
        recipe=recipe,
        panel_csv=panel_csv,
        kospi_csv=kospi_csv,
        date_from=date_from,
        date_to=date_to,
        variant_key=variant_key,
    )
    if not rows_in:
        return {"step": "t9_ensemble_holdout_ablation", "skipped": True, "reason": "no rows"}

    prior_map = _prior_completed_daily_return_by_eval_date(kospi_csv)
    overnight_map = _overnight_return_by_eval_date(kospi_csv)
    range_map = _prior_range_position_by_eval_date(kospi_csv)
    vol_map = _realized_vol_5d_by_eval_date(kospi_csv)
    base_rate, base_n, _ = _eval_directional_hit(rows_in)

    def _spotlight(overlaid: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return _spotlight_for_overlay(
            rows_in=rows_in,
            overlaid=overlaid,
            prior_map=prior_map,
            overnight_map=overnight_map,
            intraday_drawdown_map=None,
            spotlight_dates=spotlight_dates,
            range_position_map=range_map,
            realized_vol_map=vol_map,
        )

    def _eval_tier(
        *,
        tier_id: str,
        overlay: str,
        mild: float,
        vol: bool = False,
    ) -> dict[str, Any]:
        br, ov, delta, overlaid = _overlay_delta_on_rows(
            rows_in,
            overlay=overlay,
            prior_map=prior_map,
            overnight_map=overnight_map,
            intraday_map=None,
            prior_return_threshold=mild,
            rebound_guard_threshold=guard,
            session_open_composite_overnight_threshold=ovn_conservative,
            realized_vol_map=vol_map if vol else None,
            vol_regime_threshold=vol_thr if vol else None,
            range_position_map=range_map,
            prior_range_low_threshold=range_rec,
        )
        return {
            "tier_id": tier_id,
            "overlay": overlay,
            "prior_mild_threshold": mild,
            "rebound_guard_threshold": guard,
            "prior_range_low_threshold": range_rec,
            "session_open_composite_overnight_threshold": ovn_conservative,
            "vol_regime_threshold": vol_thr if vol else None,
            "baseline_hit_rate": br,
            "after_overlay_hit_rate": ov,
            "delta_hit_rate": delta,
            "n_evaluated": base_n,
            "spotlight": _spotlight(overlaid),
            "_overlaid": overlaid,
        }

    t7_row = _eval_tier(
        tier_id="T7_range_or_composite_ensemble",
        overlay="range_or_composite_conservative_bull_to_bear_rebound_guard_v0",
        mild=mild_legacy,
    )
    t8_row = _eval_tier(
        tier_id="T8_triple_causal_proxy_ensemble",
        overlay="range_or_composite_or_vol_gated_conservative_bull_to_bear_rebound_guard_v0",
        mild=mild_legacy,
        vol=True,
    )
    t10_row = _eval_tier(
        tier_id="T10_mild_and_range_or_composite_ensemble",
        overlay="mild_and_range_or_composite_conservative_bull_to_bear_rebound_guard_v0",
        mild=mild_t9,
    )
    t11_row = _eval_tier(
        tier_id="T11_mild_and_range_triple_ensemble",
        overlay="mild_and_range_or_composite_or_vol_gated_conservative_bull_to_bear_rebound_guard_v0",
        mild=mild_t9,
        vol=True,
    )

    reg_vs_t7 = _regression_fix_vs_reference(
        rows_in, t10_row["_overlaid"], t7_row["_overlaid"], audit_dates
    )

    train_dates, holdout_dates = _chronological_holdout_split(rows_in, train_ratio)
    train_rows = _filter_rows_by_dates(rows_in, train_dates)
    holdout_rows = _filter_rows_by_dates(rows_in, holdout_dates)

    best_range_train: dict[str, Any] | None = None
    for thr in range_sweep:
        thr_f = float(thr)
        _, _, train_delta, _ = _overlay_delta_on_rows(
            train_rows,
            overlay="prior_range_low_open_bull_to_bear_rebound_guard_v0",
            prior_map=prior_map,
            overnight_map=overnight_map,
            intraday_map=None,
            prior_return_threshold=mild_legacy,
            rebound_guard_threshold=guard,
            range_position_map=range_map,
            prior_range_low_threshold=thr_f,
        )
        cand = {"prior_range_low_threshold": thr_f, "train_delta_hit_rate": train_delta}
        if train_delta is not None and (
            best_range_train is None or train_delta > best_range_train.get("train_delta_hit_rate", -999)
        ):
            best_range_train = cand

    holdout_eval: dict[str, Any] = {}
    if best_range_train and holdout_rows:
        sel_thr = float(best_range_train["prior_range_low_threshold"])
        holdout_specs = (
            (
                "T7_ensemble_holdout",
                "range_or_composite_conservative_bull_to_bear_rebound_guard_v0",
                mild_legacy,
                False,
            ),
            (
                "T8_triple_ensemble_holdout",
                "range_or_composite_or_vol_gated_conservative_bull_to_bear_rebound_guard_v0",
                mild_legacy,
                True,
            ),
            (
                "T10_ensemble_holdout",
                "mild_and_range_or_composite_conservative_bull_to_bear_rebound_guard_v0",
                mild_t9,
                False,
            ),
            (
                "T11_triple_ensemble_holdout",
                "mild_and_range_or_composite_or_vol_gated_conservative_bull_to_bear_rebound_guard_v0",
                mild_t9,
                True,
            ),
        )
        for label, overlay, mild, use_vol in holdout_specs:
            _, _, hold_delta, _ = _overlay_delta_on_rows(
                holdout_rows,
                overlay=overlay,
                prior_map=prior_map,
                overnight_map=overnight_map,
                intraday_map=None,
                prior_return_threshold=mild,
                rebound_guard_threshold=guard,
                session_open_composite_overnight_threshold=ovn_conservative,
                realized_vol_map=vol_map if use_vol else None,
                vol_regime_threshold=vol_thr if use_vol else None,
                range_position_map=range_map,
                prior_range_low_threshold=sel_thr,
            )
            holdout_eval[label] = {
                "holdout_delta_hit_rate": hold_delta,
                "prior_range_low_threshold": sel_thr,
                "prior_mild_threshold": mild,
            }

    def _strip_internal(row: dict[str, Any]) -> dict[str, Any]:
        return {k: v for k, v in row.items() if not k.startswith("_")}

    t10_minus_t7_pp = (
        round(float(t10_row["delta_hit_rate"]) - float(t7_row["delta_hit_rate"]), 6)
        if t10_row.get("delta_hit_rate") is not None and t7_row.get("delta_hit_rate") is not None
        else None
    )
    t11_minus_t8_pp = (
        round(float(t11_row["delta_hit_rate"]) - float(t8_row["delta_hit_rate"]), 6)
        if t11_row.get("delta_hit_rate") is not None and t8_row.get("delta_hit_rate") is not None
        else None
    )
    hold_t7 = (holdout_eval.get("T7_ensemble_holdout") or {}).get("holdout_delta_hit_rate")
    hold_t10 = (holdout_eval.get("T10_ensemble_holdout") or {}).get("holdout_delta_hit_rate")
    hold_delta_pp = (
        round(float(hold_t10) - float(hold_t7), 6)
        if hold_t10 is not None and hold_t7 is not None
        else None
    )

    payload: dict[str, Any] = {
        "schema": "max_hypo_t9_ensemble_holdout_ablation_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "hypothesis_tag": "[MAX_HYPO][HYPO]",
        "multilens_baseline_hit_rate": base_rate,
        "n_evaluated": base_n,
        "params": {
            "rebound_guard_threshold": guard,
            "prior_mild_threshold_t9": mild_t9,
            "composite_mild_threshold_legacy": mild_legacy,
            "prior_range_low_threshold": range_rec,
            "composite_overnight_conservative": ovn_conservative,
            "vol_regime_threshold": vol_thr,
        },
        "baseline_t7": _strip_internal(t7_row),
        "baseline_t8": _strip_internal(t8_row),
        "recommended_t10": _strip_internal(t10_row),
        "recommended_t11": _strip_internal(t11_row),
        "t10_vs_t7": {
            "full_window_delta_pp": t10_minus_t7_pp,
            "holdout_delta_pp": hold_delta_pp,
            "regressions_fixed_vs_t7": reg_vs_t7.get("regressions_fixed_vs_reference"),
            "regressions_remaining_vs_t7": reg_vs_t7.get("regressions_remaining_vs_reference"),
            "regression_audit": reg_vs_t7,
        },
        "t11_minus_t8_pp": t11_minus_t8_pp,
        "holdout_split": {
            "train_ratio": train_ratio,
            "n_train_dates": len(train_dates),
            "n_holdout_dates": len(holdout_dates),
            "selected_range_threshold_on_train": best_range_train,
            "holdout_eval": holdout_eval,
        },
        "interpretation_ko": {
            "T10": "T9 mild∧range leg ∨ composite conservative; T7 대비 fold1 V-rebound 오탐 감소 기대",
            "T11": "T10 + vol-gated composite; vol-gated ⊆ composite 이면 T10과 동일 Δ 가능",
            "tradeoff": "full-window Δ는 T7보다 낮을 수 있음 — 정밀도·회귀 수정 vs recall",
        },
        "track_wall": "no_track_a_live_auto_merge",
    }

    assert_output_path_isolated(out_path.resolve())
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _write_t9_ensemble_holdout_md(payload, md_path)

    t10_clean = _strip_internal(t10_row)
    return {
        "step": "t9_ensemble_holdout_ablation",
        "output": _rel(out_path),
        "md_output": _rel(md_path),
        "t7_delta": t7_row.get("delta_hit_rate"),
        "t10_delta": t10_row.get("delta_hit_rate"),
        "t10_minus_t7_pp": t10_minus_t7_pp,
        "t11_minus_t8_pp": t11_minus_t8_pp,
        "holdout_t10_delta": hold_t10,
        "regressions_fixed_vs_t7": reg_vs_t7.get("regressions_fixed_vs_reference"),
        "regressions_remaining_vs_t7": reg_vs_t7.get("regressions_remaining_vs_reference"),
        "spotlight_safe": all(
            str(next((s for s in t10_clean.get("spotlight") or [] if s.get("date") == dk), {}).get(
                "after_overlay_predicted"
            ) or "")
            == str(next((s for s in t10_clean.get("spotlight") or [] if s.get("date") == dk), {}).get(
                "actual_direction"
            ) or "")
            for dk in spotlight_dates
            if next((s for s in t10_clean.get("spotlight") or [] if s.get("date") == dk), None)
        ),
    }


def _write_ensemble_soft_range_uplift_md(payload: dict[str, Any], md_path: Path) -> None:
    rec = payload.get("recommended") or {}
    t7 = payload.get("baseline_t7") or {}
    t10 = payload.get("baseline_t10") or {}
    lines = [
        "# MAX_HYPO T12 soft range-cap uplift recovery v1",
        "",
        "`[MAX_HYPO][HYPO]` · `research_only` · Track A / live auto-merge 없음.",
        "",
        f"- generated: {payload.get('generated_at_utc')}",
        "",
        "## Baselines",
        "",
        f"- T7 full Δ: {t7.get('delta_hit_rate')} · T10 full Δ: {t10.get('delta_hit_rate')}",
        "",
        "## T12 recommended (soft range-only leg)",
        "",
        f"- range_soft_cap: **{rec.get('range_soft_cap_for_range_only_leg')}**",
        f"- full Δ: **{rec.get('full_window_delta_hit_rate')}**",
        f"- vs T7: {payload.get('recommended_vs_t7_pp')} pp · vs T10: {payload.get('recommended_vs_t10_pp')} pp",
        f"- regressions fixed vs T7: **{rec.get('regressions_fixed_vs_t7')}** · remaining: {rec.get('regressions_remaining_vs_t7')}",
        "",
        "## Spotlight",
        "",
    ]
    for sp in rec.get("spotlight") or []:
        lines.append(
            f"- {sp.get('date')}: after={sp.get('after_overlay_predicted')} "
            f"actual={sp.get('actual_direction')} triggers={sp.get('overlay_triggers')}"
        )
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_ensemble_soft_range_uplift_ablation_sidecar(
    *,
    recipe: dict[str, Any],
    panel_csv: Path,
    kospi_csv: Path,
    date_from: str,
    date_to: str,
    spotlight_dates: list[str],
    out_path: Path,
    md_path: Path,
    dry_run: bool,
) -> dict[str, Any]:
    """T12 soft range-cap sweep: recover T7 uplift while keeping T10 regression fixes [HYPO]."""
    ablation = (
        recipe.get("ensemble_soft_range_uplift_ablation")
        if isinstance(recipe.get("ensemble_soft_range_uplift_ablation"), dict)
        else {}
    )
    guard = float(ablation.get("rebound_guard_threshold_recommended") or -0.075)
    mild_t9 = float(ablation.get("prior_mild_threshold_recommended") or -0.04)
    mild_legacy = float(ablation.get("composite_mild_threshold_legacy") or -0.048)
    ovn_conservative = float(ablation.get("composite_overnight_conservative") or -0.025)
    range_rec = float(ablation.get("prior_range_low_threshold_recommended") or 0.15)
    audit_dates = list(ablation.get("fold_regression_audit_dates") or ["2026-01-09", "2026-01-21", "2026-01-27"])
    soft_cap_sweep_raw = ablation.get("range_soft_cap_sweep")
    if soft_cap_sweep_raw is None:
        soft_cap_sweep: list[float | None] = [None, -0.025, -0.03, -0.035, -0.04]
    else:
        soft_cap_sweep = [None if v is None else float(v) for v in soft_cap_sweep_raw]
    variant_key = str(ablation.get("multilens_variant") or "operational_baseline")
    overlay_t12 = "mild_and_range_or_soft_range_or_composite_conservative_bull_to_bear_rebound_guard_v0"
    overlay_t7 = "range_or_composite_conservative_bull_to_bear_rebound_guard_v0"
    overlay_t10 = "mild_and_range_or_composite_conservative_bull_to_bear_rebound_guard_v0"

    if dry_run:
        return {"step": "ensemble_soft_range_uplift_ablation", "skipped": True, "output": _rel(out_path)}

    if not panel_csv.is_file() or not kospi_csv.is_file():
        return {"step": "ensemble_soft_range_uplift_ablation", "skipped": True, "reason": "missing panel or kospi"}

    from scripts.run_prophecy_restoration_spike import (
        _eval_directional_hit,
        _overnight_return_by_eval_date,
        _prior_completed_daily_return_by_eval_date,
        _prior_range_position_by_eval_date,
    )

    rows_in = build_multilens_eval_rows(
        recipe=recipe,
        panel_csv=panel_csv,
        kospi_csv=kospi_csv,
        date_from=date_from,
        date_to=date_to,
        variant_key=variant_key,
    )
    if not rows_in:
        return {"step": "ensemble_soft_range_uplift_ablation", "skipped": True, "reason": "no rows"}

    prior_map = _prior_completed_daily_return_by_eval_date(kospi_csv)
    overnight_map = _overnight_return_by_eval_date(kospi_csv)
    range_map = _prior_range_position_by_eval_date(kospi_csv)
    base_rate, base_n, _ = _eval_directional_hit(rows_in)

    def _spotlight(overlaid: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return _spotlight_for_overlay(
            rows_in=rows_in,
            overlaid=overlaid,
            prior_map=prior_map,
            overnight_map=overnight_map,
            intraday_drawdown_map=None,
            spotlight_dates=spotlight_dates,
            range_position_map=range_map,
        )

    def _spot_ok(spotlight: list[dict[str, Any]]) -> bool:
        return all(
            str(next((s for s in spotlight if s.get("date") == dk), {}).get("after_overlay_predicted") or "")
            == str(next((s for s in spotlight if s.get("date") == dk), {}).get("actual_direction") or "")
            for dk in spotlight_dates
            if next((s for s in spotlight if s.get("date") == dk), None)
        )

    _, _, t7_delta, overlaid_t7 = _overlay_delta_on_rows(
        rows_in,
        overlay=overlay_t7,
        prior_map=prior_map,
        overnight_map=overnight_map,
        intraday_map=None,
        prior_return_threshold=mild_legacy,
        rebound_guard_threshold=guard,
        session_open_composite_overnight_threshold=ovn_conservative,
        range_position_map=range_map,
        prior_range_low_threshold=range_rec,
    )
    _, _, t10_delta, overlaid_t10 = _overlay_delta_on_rows(
        rows_in,
        overlay=overlay_t10,
        prior_map=prior_map,
        overnight_map=overnight_map,
        intraday_map=None,
        prior_return_threshold=mild_t9,
        rebound_guard_threshold=guard,
        session_open_composite_overnight_threshold=ovn_conservative,
        range_position_map=range_map,
        prior_range_low_threshold=range_rec,
        range_soft_cap_for_range_only_leg=None,
    )

    grid: list[dict[str, Any]] = []
    for cap_raw in soft_cap_sweep:
        br, ov, delta, overlaid = _overlay_delta_on_rows(
            rows_in,
            overlay=overlay_t12,
            prior_map=prior_map,
            overnight_map=overnight_map,
            intraday_map=None,
            prior_return_threshold=mild_t9,
            rebound_guard_threshold=guard,
            session_open_composite_overnight_threshold=ovn_conservative,
            range_position_map=range_map,
            prior_range_low_threshold=range_rec,
            range_soft_cap_for_range_only_leg=cap_raw,
        )
        spotlight = _spotlight(overlaid)
        reg_vs_t7 = _regression_fix_vs_reference(rows_in, overlaid, overlaid_t7, audit_dates)
        reg_vs_t10 = _regression_fix_vs_reference(rows_in, overlaid, overlaid_t10, audit_dates)
        grid.append(
            {
                "tier_id": "T12_soft_range_cap_ensemble",
                "overlay": overlay_t12,
                "range_soft_cap_for_range_only_leg": cap_raw,
                "prior_mild_threshold": mild_t9,
                "rebound_guard_threshold": guard,
                "prior_range_low_threshold": range_rec,
                "baseline_hit_rate": br,
                "after_overlay_hit_rate": ov,
                "full_window_delta_hit_rate": delta,
                "spotlight_safe": _spot_ok(spotlight),
                "spotlight": spotlight,
                "regressions_fixed_vs_t7": reg_vs_t7.get("regressions_fixed_vs_reference"),
                "regressions_remaining_vs_t7": reg_vs_t7.get("regressions_remaining_vs_reference"),
                "regressions_remaining_vs_t10": reg_vs_t10.get("regressions_remaining_vs_reference"),
                "regression_audit_vs_t7": reg_vs_t7,
            }
        )

    safe = [
        r
        for r in grid
        if r.get("spotlight_safe")
        and (r.get("regressions_remaining_vs_t7") or 0) == 0
        and (r.get("regressions_remaining_vs_t10") or 0) == 0
    ]
    rank_pool = safe if safe else grid

    def _rank_key(row: dict[str, Any]) -> tuple:
        return (
            row.get("full_window_delta_hit_rate") or -999.0,
            row.get("regressions_fixed_vs_t7") or 0,
            row.get("wf_fold_1_test_delta_hit_rate") or -999.0,
        )

    recommended = max(rank_pool, key=_rank_key) if rank_pool else {}
    rec_vs_t7 = (
        round(float(recommended.get("full_window_delta_hit_rate") or 0) - float(t7_delta or 0), 6)
        if recommended and t7_delta is not None
        else None
    )
    rec_vs_t10 = (
        round(float(recommended.get("full_window_delta_hit_rate") or 0) - float(t10_delta or 0), 6)
        if recommended and t10_delta is not None
        else None
    )

    payload: dict[str, Any] = {
        "schema": "max_hypo_ensemble_soft_range_uplift_ablation_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "hypothesis_tag": "[MAX_HYPO][HYPO]",
        "multilens_baseline_hit_rate": base_rate,
        "n_evaluated": base_n,
        "baseline_t7": {"overlay": overlay_t7, "delta_hit_rate": t7_delta},
        "baseline_t10": {"overlay": overlay_t10, "delta_hit_rate": t10_delta},
        "t12_soft_range_cap_grid": grid,
        "recommended": recommended,
        "recommended_vs_t7_pp": rec_vs_t7,
        "recommended_vs_t10_pp": rec_vs_t10,
        "interpretation_ko": {
            "soft_cap": "prior<=cap ∧ range-low 추가 leg; +prior V-rebound(1/9) 차단, cap 완화 시 T7 uplift 회복 시도",
            "rank": "spotlight_safe ∧ T7·T10 회귀 0 잔여 우선 → full Δ 최대",
        },
        "track_wall": "no_track_a_live_auto_merge",
    }

    assert_output_path_isolated(out_path.resolve())
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _write_ensemble_soft_range_uplift_md(payload, md_path)

    return {
        "step": "ensemble_soft_range_uplift_ablation",
        "output": _rel(out_path),
        "md_output": _rel(md_path),
        "t7_delta": t7_delta,
        "t10_delta": t10_delta,
        "t12_recommended_delta": recommended.get("full_window_delta_hit_rate"),
        "recommended_soft_cap": recommended.get("range_soft_cap_for_range_only_leg"),
        "recommended_vs_t7_pp": rec_vs_t7,
        "recommended_vs_t10_pp": rec_vs_t10,
        "regressions_remaining_vs_t7": recommended.get("regressions_remaining_vs_t7"),
        "spotlight_safe": recommended.get("spotlight_safe"),
    }


def _load_optional_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return doc if isinstance(doc, dict) else None


def _write_recommended_tier_manifest_md(payload: dict[str, Any], md_path: Path) -> None:
    rec = payload.get("recommended") or {}
    lines = [
        "# MAX_HYPO recommended sandbox tier manifest v1",
        "",
        "`[MAX_HYPO][HYPO]` · `research_only` · Track A / live auto-merge 없음.",
        "",
        f"- generated: {payload.get('generated_at_utc')}",
        f"- recommended tier: **{rec.get('tier_id')}**",
        f"- overlay: `{rec.get('overlay')}`",
        "",
        "## Params",
        "",
    ]
    for k, v in (rec.get("params") or {}).items():
        lines.append(f"- {k}: {v}")
    lines.extend(
        [
            "",
            "## Metrics",
            "",
            f"- full Δ: **{rec.get('full_window_delta_hit_rate')}** · vs T7: {rec.get('vs_t7_pp')} pp",
            f"- regressions fixed vs T7: {rec.get('regressions_fixed_vs_t7')} · remaining: {rec.get('regressions_remaining_vs_t7')}",
            "",
            "## Spotlight",
            "",
        ]
    )
    for sp in rec.get("spotlight") or []:
        lines.append(
            f"- {sp.get('date')}: after={sp.get('after_overlay_predicted')} actual={sp.get('actual_direction')}"
        )
    lines.extend(["", "## Tradeoff", "", str(payload.get("tradeoff_ko") or "")])
    tradeoff_ptr = (payload.get("evidence_pointers") or {}).get("closure_tradeoff_md") or {}
    if tradeoff_ptr.get("path"):
        lines.extend(
            [
                "",
                "## Closure tradeoff (full)",
                "",
                f"- see: `{tradeoff_ptr.get('path')}`",
            ]
        )
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_composite_overnight_mild_gate_ablation_sidecar(
    *,
    recipe: dict[str, Any],
    panel_csv: Path,
    kospi_csv: Path,
    date_from: str,
    date_to: str,
    spotlight_dates: list[str],
    out_path: Path,
    md_path: Path,
    dry_run: bool,
) -> dict[str, Any]:
    """T13 overnight mild-gate vs T10 baseline ensemble [HYPO]."""
    ablation = (
        recipe.get("composite_overnight_mild_gate_ablation")
        if isinstance(recipe.get("composite_overnight_mild_gate_ablation"), dict)
        else {}
    )
    guard = float(ablation.get("rebound_guard_threshold_recommended") or -0.075)
    mild_t9 = float(ablation.get("prior_mild_threshold_recommended") or -0.04)
    ovn_conservative = float(ablation.get("composite_overnight_conservative") or -0.025)
    range_rec = float(ablation.get("prior_range_low_threshold_recommended") or 0.15)
    audit_dates = list(ablation.get("fold_regression_audit_dates") or ["2026-01-09", "2026-01-21", "2026-01-27"])
    variant_key = str(ablation.get("multilens_variant") or "operational_baseline")
    overlay_t10 = "mild_and_range_or_composite_conservative_bull_to_bear_rebound_guard_v0"
    overlay_t13 = "mild_and_range_or_composite_overnight_mild_gated_conservative_bull_to_bear_rebound_guard_v0"
    overlay_t7 = "range_or_composite_conservative_bull_to_bear_rebound_guard_v0"
    mild_legacy = float(ablation.get("composite_mild_threshold_legacy") or -0.048)

    if dry_run:
        return {"step": "composite_overnight_mild_gate_ablation", "skipped": True, "output": _rel(out_path)}

    if not panel_csv.is_file() or not kospi_csv.is_file():
        return {"step": "composite_overnight_mild_gate_ablation", "skipped": True, "reason": "missing panel or kospi"}

    from scripts.run_prophecy_restoration_spike import (
        _eval_directional_hit,
        _overnight_return_by_eval_date,
        _prior_completed_daily_return_by_eval_date,
        _prior_range_position_by_eval_date,
    )

    rows_in = build_multilens_eval_rows(
        recipe=recipe,
        panel_csv=panel_csv,
        kospi_csv=kospi_csv,
        date_from=date_from,
        date_to=date_to,
        variant_key=variant_key,
    )
    if not rows_in:
        return {"step": "composite_overnight_mild_gate_ablation", "skipped": True, "reason": "no rows"}

    prior_map = _prior_completed_daily_return_by_eval_date(kospi_csv)
    overnight_map = _overnight_return_by_eval_date(kospi_csv)
    range_map = _prior_range_position_by_eval_date(kospi_csv)
    base_rate, base_n, _ = _eval_directional_hit(rows_in)

    def _eval_tier(tier_id: str, overlay: str) -> dict[str, Any]:
        br, ov, delta, overlaid = _overlay_delta_on_rows(
            rows_in,
            overlay=overlay,
            prior_map=prior_map,
            overnight_map=overnight_map,
            intraday_map=None,
            prior_return_threshold=mild_t9,
            rebound_guard_threshold=guard,
            session_open_composite_overnight_threshold=ovn_conservative,
            range_position_map=range_map,
            prior_range_low_threshold=range_rec,
        )
        spotlight = _spotlight_for_overlay(
            rows_in=rows_in,
            overlaid=overlaid,
            prior_map=prior_map,
            overnight_map=overnight_map,
            intraday_drawdown_map=None,
            spotlight_dates=spotlight_dates,
            range_position_map=range_map,
        )
        spot_ok = all(
            str(next((s for s in spotlight if s.get("date") == dk), {}).get("after_overlay_predicted") or "")
            == str(next((s for s in spotlight if s.get("date") == dk), {}).get("actual_direction") or "")
            for dk in spotlight_dates
            if next((s for s in spotlight if s.get("date") == dk), None)
        )
        return {
            "tier_id": tier_id,
            "overlay": overlay,
            "baseline_hit_rate": br,
            "after_overlay_hit_rate": ov,
            "full_window_delta_hit_rate": delta,
            "spotlight_safe": spot_ok,
            "spotlight": spotlight,
            "_overlaid": overlaid,
        }

    _, _, _, overlaid_t7 = _overlay_delta_on_rows(
        rows_in,
        overlay=overlay_t7,
        prior_map=prior_map,
        overnight_map=overnight_map,
        intraday_map=None,
        prior_return_threshold=mild_legacy,
        rebound_guard_threshold=guard,
        session_open_composite_overnight_threshold=ovn_conservative,
        range_position_map=range_map,
        prior_range_low_threshold=range_rec,
    )
    t10 = _eval_tier("T10_mild_and_range_or_composite_ensemble", overlay_t10)
    t13 = _eval_tier("T13_overnight_mild_gated_ensemble", overlay_t13)
    reg_t10 = _regression_fix_vs_reference(rows_in, t10["_overlaid"], overlaid_t7, audit_dates)
    reg_t13 = _regression_fix_vs_reference(rows_in, t13["_overlaid"], overlaid_t7, audit_dates)

    def _strip(row: dict[str, Any]) -> dict[str, Any]:
        out = {k: v for k, v in row.items() if not k.startswith("_")}
        return out

    t10_s = _strip(t10)
    t13_s = _strip(t13)
    t10_s["regressions_fixed_vs_t7"] = reg_t10.get("regressions_fixed_vs_reference")
    t10_s["regressions_remaining_vs_t7"] = reg_t10.get("regressions_remaining_vs_reference")
    t13_s["regressions_fixed_vs_t7"] = reg_t13.get("regressions_fixed_vs_reference")
    t13_s["regressions_remaining_vs_t7"] = reg_t13.get("regressions_remaining_vs_reference")

    candidates = [t10_s, t13_s]
    safe = [
        r
        for r in candidates
        if r.get("spotlight_safe")
        and (r.get("regressions_remaining_vs_t7") or 0) == 0
    ]
    pool = safe if safe else candidates
    recommended = max(pool, key=lambda r: r.get("full_window_delta_hit_rate") or -999.0)

    t13_minus_t10 = (
        round(float(t13_s.get("full_window_delta_hit_rate") or 0) - float(t10_s.get("full_window_delta_hit_rate") or 0), 6)
        if t13_s.get("full_window_delta_hit_rate") is not None and t10_s.get("full_window_delta_hit_rate") is not None
        else None
    )

    payload: dict[str, Any] = {
        "schema": "max_hypo_composite_overnight_mild_gate_ablation_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "hypothesis_tag": "[MAX_HYPO][HYPO]",
        "multilens_baseline_hit_rate": base_rate,
        "n_evaluated": base_n,
        "baseline_t10": t10_s,
        "candidate_t13": t13_s,
        "t13_minus_t10_pp": t13_minus_t10,
        "recommended": recommended,
        "interpretation_ko": {
            "gate": "overnight_gap는 prior_mild 동반 시만 bear; overnight-only 단독 발화 차단",
            "pick": "spotlight_safe ∧ T7 회귀 0 잔여 → full Δ 최대",
        },
        "track_wall": "no_track_a_live_auto_merge",
    }

    assert_output_path_isolated(out_path.resolve())
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(
        "\n".join(
            [
                "# MAX_HYPO T13 overnight mild-gate v1",
                "",
                f"- T10 Δ: {t10_s.get('full_window_delta_hit_rate')} · T13 Δ: {t13_s.get('full_window_delta_hit_rate')}",
                f"- T13−T10: {t13_minus_t10} pp · recommended: {recommended.get('tier_id')}",
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    return {
        "step": "composite_overnight_mild_gate_ablation",
        "output": _rel(out_path),
        "md_output": _rel(md_path),
        "t10_delta": t10_s.get("full_window_delta_hit_rate"),
        "t13_delta": t13_s.get("full_window_delta_hit_rate"),
        "t13_minus_t10_pp": t13_minus_t10,
        "recommended_tier": recommended.get("tier_id"),
        "spotlight_safe": recommended.get("spotlight_safe"),
    }


def run_recommended_tier_manifest_sidecar(
    *,
    recipe: dict[str, Any],
    out_path: Path,
    md_path: Path,
    dry_run: bool,
) -> dict[str, Any]:
    """Aggregate sandbox evidence into a single recommended tier manifest [HYPO]."""
    cfg = (
        recipe.get("max_hypo_recommended_tier_manifest")
        if isinstance(recipe.get("max_hypo_recommended_tier_manifest"), dict)
        else {}
    )
    tradeoff_md = ROOT / str(
        cfg.get("tradeoff_md_output") or "reports/max_hypo_sandbox_closure_tradeoff_v1.md"
    )
    evidence = cfg.get("evidence_artifacts") if isinstance(cfg.get("evidence_artifacts"), dict) else {}
    te_path = ROOT / str(
        evidence.get("t9_ensemble_holdout")
        or "experiments/max_hypo_unbound/results/max_hypo_t9_ensemble_holdout_ablation_v1.json"
    )
    uplift_path = ROOT / str(
        evidence.get("ensemble_soft_range_uplift")
        or "experiments/max_hypo_unbound/results/max_hypo_ensemble_soft_range_uplift_ablation_v1.json"
    )
    conj_path = ROOT / str(
        evidence.get("prior_mild_range_conjunction")
        or "experiments/max_hypo_unbound/results/max_hypo_prior_mild_range_conjunction_ablation_v1.json"
    )
    ovn_path = ROOT / str(
        evidence.get("composite_overnight_mild_gate")
        or "experiments/max_hypo_unbound/results/max_hypo_composite_overnight_mild_gate_ablation_v1.json"
    )

    if dry_run:
        return {"step": "recommended_tier_manifest", "skipped": True, "output": _rel(out_path)}

    te_doc = _load_optional_json(te_path)
    uplift_doc = _load_optional_json(uplift_path)
    conj_doc = _load_optional_json(conj_path)
    ovn_doc = _load_optional_json(ovn_path)

    t10 = (te_doc or {}).get("recommended_t10") or {}
    t7_delta = ((te_doc or {}).get("baseline_t7") or {}).get("delta_hit_rate")
    t10_vs_t7 = (te_doc or {}).get("t10_vs_t7") or {}
    ovn_rec = (ovn_doc or {}).get("recommended") or {}
    uplift_rec = (uplift_doc or {}).get("recommended") or {}

    pick = t10
    tier_id = str(pick.get("tier_id") or "T10_mild_and_range_or_composite_ensemble")
    overlay = str(
        pick.get("overlay") or "mild_and_range_or_composite_conservative_bull_to_bear_rebound_guard_v0"
    )
    delta = pick.get("delta_hit_rate")
    spotlight = pick.get("spotlight") or []
    reg_fixed = t10_vs_t7.get("regressions_fixed_vs_t7")
    reg_remaining = t10_vs_t7.get("regressions_remaining_vs_t7")

    if (
        ovn_rec.get("tier_id") == "T13_overnight_mild_gated_ensemble"
        and ovn_rec.get("spotlight_safe")
        and (ovn_rec.get("regressions_remaining_vs_t7") or 0) == 0
        and (ovn_rec.get("full_window_delta_hit_rate") or 0) > (delta or 0)
    ):
        tier_id = str(ovn_rec.get("tier_id"))
        overlay = str(ovn_rec.get("overlay") or overlay)
        delta = ovn_rec.get("full_window_delta_hit_rate")
        spotlight = ovn_rec.get("spotlight") or spotlight
        reg_fixed = ovn_rec.get("regressions_fixed_vs_t7")
        reg_remaining = ovn_rec.get("regressions_remaining_vs_t7")

    vs_t7 = (
        round(float(delta) - float(t7_delta), 6)
        if delta is not None and t7_delta is not None
        else t10_vs_t7.get("full_window_delta_pp")
    )

    tradeoff = (
        "T10: mild∧range ∨ composite( prior_mild ∨ overnight ). T7 대비 정밀도↑(1/9·1/21·1/27 회귀 수정) · recall↓. "
        "T12 soft-cap sweep은 T10과 동일 Pareto. Track A 승격·실매매 자동 합선 없음."
    )
    if uplift_rec.get("range_soft_cap_for_range_only_leg") is None:
        tradeoff += " T12 권장 cap=None."

    recommended = {
        "tier_id": tier_id,
        "overlay": overlay,
        "params": {
            "prior_mild_threshold": pick.get("prior_mild_threshold") or -0.04,
            "rebound_guard_threshold": pick.get("rebound_guard_threshold") or -0.075,
            "prior_range_low_threshold": pick.get("prior_range_low_threshold") or 0.15,
            "session_open_composite_overnight_threshold": pick.get("session_open_composite_overnight_threshold")
            or -0.025,
        },
        "full_window_delta_hit_rate": delta,
        "vs_t7_pp": vs_t7,
        "regressions_fixed_vs_t7": reg_fixed,
        "regressions_remaining_vs_t7": reg_remaining,
        "spotlight": spotlight,
        "standalone_t9_note": (conj_doc or {}).get("recommended") or {},
    }

    payload: dict[str, Any] = {
        "schema": "max_hypo_recommended_tier_manifest_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "hypothesis_tag": "[MAX_HYPO][HYPO]",
        "recommended": recommended,
        "tradeoff_ko": tradeoff,
        "evidence_pointers": {
            "t9_ensemble_holdout": {"path": _rel(te_path), "loaded": te_doc is not None},
            "ensemble_soft_range_uplift": {"path": _rel(uplift_path), "loaded": uplift_doc is not None},
            "prior_mild_range_conjunction": {"path": _rel(conj_path), "loaded": conj_doc is not None},
            "composite_overnight_mild_gate": {"path": _rel(ovn_path), "loaded": ovn_doc is not None},
            "closure_tradeoff_md": {
                "path": _rel(tradeoff_md),
                "loaded": tradeoff_md.is_file(),
            },
        },
        "track_wall": "no_track_a_live_auto_merge",
    }

    assert_output_path_isolated(out_path.resolve())
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _write_recommended_tier_manifest_md(payload, md_path)

    return {
        "step": "recommended_tier_manifest",
        "output": _rel(out_path),
        "md_output": _rel(md_path),
        "recommended_tier": tier_id,
        "recommended_delta": delta,
        "vs_t7_pp": vs_t7,
        "spotlight_safe": all(
            str(sp.get("after_overlay_predicted") or "") == str(sp.get("actual_direction") or "")
            for sp in spotlight
            if sp.get("date")
        ),
    }


def shock_day_audit(
    *,
    recipe: dict[str, Any],
    kospi_csv: Path,
    panel_csv: Path,
    spotlight_dates: list[str],
) -> dict[str, Any]:
    from scripts.build_kospi_june2026_daily_prophecy_calendar_v1 import _read_json
    from scripts.kospi_june2026_multilens_blend_v1 import load_ensemble_kospi_per_date, load_static_lenses
    from scripts.run_kospi_multilens_blend_backtest_v1 import (
        EVOLUTION_RULES as RULES_PATH,
        _direction_from_return,
        _load_closes,
        _load_panel,
        _predict_v2,
    )

    shock = recipe.get("shock_overlay") if isinstance(recipe.get("shock_overlay"), dict) else {}
    thr_pct = float(shock.get("prior_shock_threshold_pct") or 4.0)
    rules = _read_json(RULES_PATH)
    panel = _load_panel(panel_csv)
    closes = _load_closes(kospi_csv)
    static_lenses = load_static_lenses()
    neutral_band = float(rules.get("neutral_band", 0.06))
    blend_policy = dict(rules.get("blend_policy_v2") or {})
    coord_policy = dict(rules.get("four_ai_coordinator_policy") or {})
    ensemble_by_date = load_ensemble_kospi_per_date([d for d in spotlight_dates if d in panel])
    sorted_dates = sorted(closes.keys())
    prior_by_date: dict[str, float] = {}
    for i in range(1, len(sorted_dates)):
        d = sorted_dates[i]
        p0, p1 = closes[sorted_dates[i - 1]], closes[d]
        if p0:
            prior_by_date[d] = (p1 - p0) / p0

    shock_dates = [d for d, r in prior_by_date.items() if abs(r) * 100.0 >= thr_pct]
    neutral_bps = float(recipe.get("decision_mode", {}).get("neutral_bps_reference") or 2.0)
    catalog = {**operational_baseline_catalog(recipe), **max_hypo_catalog(recipe)}
    spotlight_rows: list[dict[str, Any]] = []
    for dk in spotlight_dates:
        if dk not in closes:
            spotlight_rows.append({"date": dk, "status": "missing_close"})
            continue
        idx = sorted_dates.index(dk)
        if idx < 1:
            spotlight_rows.append({"date": dk, "status": "no_prior_session"})
            continue
        prev = sorted_dates[idx - 1]
        prev_close = closes[prev]
        act_ret = (closes[dk] - prev_close) / prev_close if prev_close else 0.0
        actual = _direction_from_return(act_ret, neutral_bps)
        row_out: dict[str, Any] = {
            "date": dk,
            "prior_day_return_pct": round(prior_by_date.get(dk, 0.0) * 100.0, 4),
            "session_return_pct": round(act_ret * 100.0, 4),
            "actual_direction": actual,
            "predictions": {},
        }
        if dk not in panel:
            row_out["status"] = "missing_panel_row"
            row_out["note"] = "명리 session panel stale — extend panel CSV for per-date lens preds"
            spotlight_rows.append(row_out)
            continue
        ens_row = ensemble_by_date.get(dk)
        for vid, spec in catalog.items():
            pred, _meta = _predict_v2(
                dk,
                panel_row=panel[dk],
                closes=closes,
                static_lenses=static_lenses,
                ensemble_row=ens_row,
                weights=spec["weights"],
                blend_policy=blend_policy,
                neutral_band=neutral_band,
                four_ai_mode="current",
                coord_policy=coord_policy,
            )
            row_out["predictions"][vid] = pred
        spotlight_rows.append(row_out)
    return {
        "step": "shock_day_audit",
        "prior_shock_threshold_pct": thr_pct,
        "n_shock_days_in_series": len(shock_dates),
        "recent_shock_dates_tail": shock_dates[-8:],
        "spotlight": spotlight_rows,
    }


def fills_cache_summary(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"present": False, "path": _rel(path)}
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    daily = doc.get("daily_by_utc_date") if isinstance(doc.get("daily_by_utc_date"), dict) else {}
    stats = doc.get("stats") if isinstance(doc.get("stats"), dict) else {}
    return {
        "present": True,
        "path": _rel(path),
        "n_daily_buckets": stats.get("n_daily_buckets", len(daily)),
        "n_fill_rows": stats.get("n_fill_rows"),
        "schema": doc.get("schema"),
        "date_min": min(daily.keys()) if daily else None,
        "date_max": max(daily.keys()) if daily else None,
    }


def build_report(
    *,
    recipe_path: Path,
    steps: list[dict[str, Any]],
    dry_run: bool,
) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "label": MAX_HYPO_LABEL,
        "research_only": True,
        "source_track": "B",
        "track_wall": {
            "prod_score_mutation": False,
            "track_a_auto_bridge": False,
            "live_trading": False,
            "fail_comp_004": "results never auto-promote to Track A or live routing",
        },
        "recipe_path": _rel(recipe_path),
        "dry_run": dry_run,
        "forbidden_claims": [
            "track_a_promotion_from_max_hypo",
            "live_trading_trigger",
            "operational_headline_overwrite",
            "repair_v2_as_core_model_proof",
        ],
        "boundary_ack": (
            "Internal module bulkhead removed inside sandbox only; "
            "outer wall to Track A / VPS live unchanged."
        ),
        "steps": steps,
        "operator_lines": [
            f"- {MAX_HYPO_LABEL} sandbox only — human sign-off before any prod experiment.",
            "- raw vs repair_v2: this lane reports sandbox metrics only; not Track A gate.",
            "- Logos lens remains [NON_GATING] in max recipe (weight 0).",
            "- shock ablation sidecar: prior_day_shock bear→neutral only; not V-rebound bull fix.",
            "- bull_abstain sidecar: multilens bull→neutral/bear after prior shock [HYPO]; sandbox only.",
            "- rebound_guard sidecar: mild prior + extreme-prior V-rebound skip; overnight gap open-only.",
            "- intraday_proxy sidecar: session-open composite (causal) + open→low oracle ceiling (not causal).",
            "- causal_open_limit sidecar: tier ladder (overnight/prior/composite/oracle) + blocked WF on composite.",
            "- vol_range_proxy sidecar: prior-range-low open + vol-gated composite + conservative WF.",
            "- ensemble_holdout sidecar: T7 range∨composite + T8 triple + holdout/fold-day audit.",
            "- range_rebound_refinement: guard sweep + overnight gap-up skip on T5 range; summary MD.",
            "- prior_mild_range_conjunction: T9 mild∧range vs T5 range-only; fold1 regression fix.",
            "- t9_ensemble_holdout: T10/T11 (T9 AND range leg ∨ composite) vs T7/T8 + holdout.",
            "- ensemble_soft_range_uplift: T12 soft range-cap sweep vs T7/T10.",
            "- composite_overnight_mild_gate: T13 overnight mild-gate vs T10.",
            "- recommended_tier_manifest: sandbox SSOT tier pick + evidence pointers.",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--recipe-json", type=Path, default=DEFAULT_RECIPE)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--lut-json", type=Path, default=DEFAULT_LUT)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--panel-csv", type=Path, default=DEFAULT_PANEL)
    ap.add_argument("--kospi-csv", type=Path, default=KOSPI_CSV)
    ap.add_argument("--btc-csv", type=Path, default=BTC_CSV)
    ap.add_argument("--fills-cache", type=Path, default=FILLS_CACHE)
    ap.add_argument(
        "--spotlight-dates",
        default="2026-06-08,2026-06-09",
        help="Comma-separated dates for shock spotlight audit.",
    )
    ap.add_argument("--dry-run", action="store_true", help="Plan only; skip heavy compute.")
    ap.add_argument("--skip-walkforward", action="store_true")
    ap.add_argument("--skip-multilens", action="store_true")
    ap.add_argument("--skip-neutral-sweep", action="store_true")
    ap.add_argument("--skip-shock-ablation", action="store_true")
    ap.add_argument("--skip-bull-abstain-ablation", action="store_true")
    ap.add_argument("--skip-rebound-guard-ablation", action="store_true")
    ap.add_argument("--skip-intraday-shock-ablation", action="store_true")
    ap.add_argument("--skip-causal-open-limit-ablation", action="store_true")
    ap.add_argument("--skip-causal-vol-range-ablation", action="store_true")
    ap.add_argument("--skip-causal-ensemble-holdout-ablation", action="store_true")
    ap.add_argument("--skip-range-rebound-guard-refinement", action="store_true")
    ap.add_argument("--skip-prior-mild-range-conjunction", action="store_true")
    ap.add_argument("--skip-t9-ensemble-holdout-ablation", action="store_true")
    ap.add_argument("--skip-ensemble-soft-range-uplift-ablation", action="store_true")
    ap.add_argument("--skip-composite-overnight-mild-gate-ablation", action="store_true")
    ap.add_argument("--skip-recommended-tier-manifest", action="store_true")
    args = ap.parse_args(argv)

    assert_output_path_isolated(args.output.resolve())
    recipe = load_recipe(args.recipe_json)
    spotlight = [d.strip()[:10] for d in str(args.spotlight_dates).split(",") if d.strip()]

    score_json = args.score_json
    if not score_json.is_file() and DEFAULT_SCORE_FALLBACK.is_file():
        score_json = DEFAULT_SCORE_FALLBACK

    steps: list[dict[str, Any]] = []
    steps.append({"step": "fills_cache", **fills_cache_summary(args.fills_cache)})

    lut_step = ensure_ohlcv_lut(
        recipe=recipe,
        kospi_csv=args.kospi_csv,
        btc_csv=args.btc_csv,
        lut_path=args.lut_json,
        dry_run=args.dry_run,
    )
    steps.append(lut_step)

    if args.dry_run:
        date_from, date_to = "2025-06-01", "2026-06-09"
    else:
        date_from, date_to = _date_window_from_lut(args.lut_json)

    if not args.skip_multilens:
        steps.append(
            run_multilens_arms(
                recipe=recipe,
                panel_csv=args.panel_csv,
                kospi_csv=args.kospi_csv,
                date_from=date_from,
                date_to=date_to,
                dry_run=args.dry_run,
            )
        )
    if not args.skip_neutral_sweep:
        steps.append(
            run_neutral_band_sweep(
                recipe=recipe,
                panel_csv=args.panel_csv,
                kospi_csv=args.kospi_csv,
                date_from=date_from,
                date_to=date_to,
                dry_run=args.dry_run,
            )
        )
    if not args.skip_walkforward and score_json.is_file():
        wf_out = SANDBOX_ROOT / "results" / "max_hypo_walkforward_sidecar_v1.json"
        assert_output_path_isolated(wf_out.resolve())
        steps.append(
            run_walkforward(
                recipe=recipe,
                score_json=score_json,
                lut_path=args.lut_json,
                wf_out=wf_out,
                dry_run=args.dry_run,
            )
        )
    elif not args.skip_walkforward:
        steps.append(
            {
                "step": "walkforward",
                "skipped": True,
                "reason": f"missing score-json: {_rel(score_json)}",
            }
        )

    if not args.skip_shock_ablation:
        ablation_cfg = recipe.get("shock_overlay_ablation") if isinstance(recipe.get("shock_overlay_ablation"), dict) else {}
        ablation_out = ROOT / str(ablation_cfg.get("sidecar_output") or "experiments/max_hypo_unbound/results/max_hypo_shock_overlay_ablation_v1.json")
        steps.append(
            run_shock_overlay_ablation_sidecar(
                recipe=recipe,
                score_json=score_json,
                kospi_csv=args.kospi_csv,
                spotlight_dates=spotlight,
                out_path=ablation_out,
                dry_run=args.dry_run,
            )
        )

    if not args.skip_bull_abstain_ablation:
        bull_cfg = (
            recipe.get("bull_abstain_overlay_ablation")
            if isinstance(recipe.get("bull_abstain_overlay_ablation"), dict)
            else {}
        )
        bull_out = ROOT / str(
            bull_cfg.get("sidecar_output")
            or "experiments/max_hypo_unbound/results/max_hypo_bull_abstain_overlay_ablation_v1.json"
        )
        steps.append(
            run_bull_abstain_overlay_ablation_sidecar(
                recipe=recipe,
                panel_csv=args.panel_csv,
                kospi_csv=args.kospi_csv,
                date_from=date_from,
                date_to=date_to,
                spotlight_dates=spotlight,
                out_path=bull_out,
                dry_run=args.dry_run,
            )
        )

    if not args.skip_rebound_guard_ablation:
        rg_cfg = (
            recipe.get("shock_rebound_guard_ablation")
            if isinstance(recipe.get("shock_rebound_guard_ablation"), dict)
            else {}
        )
        rg_out = ROOT / str(
            rg_cfg.get("sidecar_output")
            or "experiments/max_hypo_unbound/results/max_hypo_shock_rebound_guard_ablation_v1.json"
        )
        steps.append(
            run_shock_rebound_guard_ablation_sidecar(
                recipe=recipe,
                panel_csv=args.panel_csv,
                kospi_csv=args.kospi_csv,
                date_from=date_from,
                date_to=date_to,
                spotlight_dates=spotlight,
                out_path=rg_out,
                dry_run=args.dry_run,
            )
        )

    if not args.skip_intraday_shock_ablation:
        intra_cfg = (
            recipe.get("intraday_shock_proxy_ablation")
            if isinstance(recipe.get("intraday_shock_proxy_ablation"), dict)
            else {}
        )
        intra_out = ROOT / str(
            intra_cfg.get("sidecar_output")
            or "experiments/max_hypo_unbound/results/max_hypo_intraday_shock_proxy_ablation_v1.json"
        )
        steps.append(
            run_intraday_shock_proxy_ablation_sidecar(
                recipe=recipe,
                panel_csv=args.panel_csv,
                kospi_csv=args.kospi_csv,
                date_from=date_from,
                date_to=date_to,
                spotlight_dates=spotlight,
                out_path=intra_out,
                dry_run=args.dry_run,
            )
        )

    if not args.skip_causal_open_limit_ablation:
        col_cfg = (
            recipe.get("causal_open_limit_ablation")
            if isinstance(recipe.get("causal_open_limit_ablation"), dict)
            else {}
        )
        col_out = ROOT / str(
            col_cfg.get("sidecar_output")
            or "experiments/max_hypo_unbound/results/max_hypo_causal_open_limit_ablation_v1.json"
        )
        steps.append(
            run_causal_open_limit_ablation_sidecar(
                recipe=recipe,
                panel_csv=args.panel_csv,
                kospi_csv=args.kospi_csv,
                date_from=date_from,
                date_to=date_to,
                spotlight_dates=spotlight,
                out_path=col_out,
                dry_run=args.dry_run,
            )
        )

    if not args.skip_causal_vol_range_ablation:
        vrp_cfg = (
            recipe.get("causal_vol_range_proxy_ablation")
            if isinstance(recipe.get("causal_vol_range_proxy_ablation"), dict)
            else {}
        )
        vrp_out = ROOT / str(
            vrp_cfg.get("sidecar_output")
            or "experiments/max_hypo_unbound/results/max_hypo_causal_vol_range_proxy_ablation_v1.json"
        )
        steps.append(
            run_causal_vol_range_proxy_ablation_sidecar(
                recipe=recipe,
                panel_csv=args.panel_csv,
                kospi_csv=args.kospi_csv,
                date_from=date_from,
                date_to=date_to,
                spotlight_dates=spotlight,
                out_path=vrp_out,
                dry_run=args.dry_run,
            )
        )

    if not args.skip_causal_ensemble_holdout_ablation:
        enh_cfg = (
            recipe.get("causal_proxy_ensemble_holdout_ablation")
            if isinstance(recipe.get("causal_proxy_ensemble_holdout_ablation"), dict)
            else {}
        )
        enh_out = ROOT / str(
            enh_cfg.get("sidecar_output")
            or "experiments/max_hypo_unbound/results/max_hypo_causal_proxy_ensemble_holdout_ablation_v1.json"
        )
        steps.append(
            run_causal_proxy_ensemble_holdout_ablation_sidecar(
                recipe=recipe,
                panel_csv=args.panel_csv,
                kospi_csv=args.kospi_csv,
                date_from=date_from,
                date_to=date_to,
                spotlight_dates=spotlight,
                out_path=enh_out,
                dry_run=args.dry_run,
            )
        )

    if not args.skip_range_rebound_guard_refinement:
        rrr_cfg = (
            recipe.get("range_rebound_guard_refinement")
            if isinstance(recipe.get("range_rebound_guard_refinement"), dict)
            else {}
        )
        rrr_out = ROOT / str(
            rrr_cfg.get("sidecar_output")
            or "experiments/max_hypo_unbound/results/max_hypo_range_rebound_guard_refinement_v1.json"
        )
        rrr_md = ROOT / str(
            rrr_cfg.get("summary_md_output")
            or "reports/max_hypo_range_rebound_refinement_summary_v1.md"
        )
        steps.append(
            run_range_rebound_guard_refinement_sidecar(
                recipe=recipe,
                panel_csv=args.panel_csv,
                kospi_csv=args.kospi_csv,
                date_from=date_from,
                date_to=date_to,
                spotlight_dates=spotlight,
                out_path=rrr_out,
                md_path=rrr_md,
                dry_run=args.dry_run,
            )
        )

    if not args.skip_prior_mild_range_conjunction:
        pmc_cfg = (
            recipe.get("prior_mild_range_conjunction_ablation")
            if isinstance(recipe.get("prior_mild_range_conjunction_ablation"), dict)
            else {}
        )
        pmc_out = ROOT / str(
            pmc_cfg.get("sidecar_output")
            or "experiments/max_hypo_unbound/results/max_hypo_prior_mild_range_conjunction_ablation_v1.json"
        )
        pmc_md = ROOT / str(
            pmc_cfg.get("summary_md_output")
            or "reports/max_hypo_prior_mild_range_conjunction_summary_v1.md"
        )
        steps.append(
            run_prior_mild_range_conjunction_ablation_sidecar(
                recipe=recipe,
                panel_csv=args.panel_csv,
                kospi_csv=args.kospi_csv,
                date_from=date_from,
                date_to=date_to,
                spotlight_dates=spotlight,
                out_path=pmc_out,
                md_path=pmc_md,
                dry_run=args.dry_run,
            )
        )

    if not args.skip_t9_ensemble_holdout_ablation:
        te_cfg = (
            recipe.get("t9_ensemble_holdout_ablation")
            if isinstance(recipe.get("t9_ensemble_holdout_ablation"), dict)
            else {}
        )
        te_out = ROOT / str(
            te_cfg.get("sidecar_output")
            or "experiments/max_hypo_unbound/results/max_hypo_t9_ensemble_holdout_ablation_v1.json"
        )
        te_md = ROOT / str(
            te_cfg.get("summary_md_output") or "reports/max_hypo_t9_ensemble_holdout_summary_v1.md"
        )
        steps.append(
            run_t9_ensemble_holdout_ablation_sidecar(
                recipe=recipe,
                panel_csv=args.panel_csv,
                kospi_csv=args.kospi_csv,
                date_from=date_from,
                date_to=date_to,
                spotlight_dates=spotlight,
                out_path=te_out,
                md_path=te_md,
                dry_run=args.dry_run,
            )
        )

    if not args.skip_ensemble_soft_range_uplift_ablation:
        es_cfg = (
            recipe.get("ensemble_soft_range_uplift_ablation")
            if isinstance(recipe.get("ensemble_soft_range_uplift_ablation"), dict)
            else {}
        )
        es_out = ROOT / str(
            es_cfg.get("sidecar_output")
            or "experiments/max_hypo_unbound/results/max_hypo_ensemble_soft_range_uplift_ablation_v1.json"
        )
        es_md = ROOT / str(
            es_cfg.get("summary_md_output") or "reports/max_hypo_ensemble_soft_range_uplift_summary_v1.md"
        )
        steps.append(
            run_ensemble_soft_range_uplift_ablation_sidecar(
                recipe=recipe,
                panel_csv=args.panel_csv,
                kospi_csv=args.kospi_csv,
                date_from=date_from,
                date_to=date_to,
                spotlight_dates=spotlight,
                out_path=es_out,
                md_path=es_md,
                dry_run=args.dry_run,
            )
        )

    if not args.skip_composite_overnight_mild_gate_ablation:
        og_cfg = (
            recipe.get("composite_overnight_mild_gate_ablation")
            if isinstance(recipe.get("composite_overnight_mild_gate_ablation"), dict)
            else {}
        )
        og_out = ROOT / str(
            og_cfg.get("sidecar_output")
            or "experiments/max_hypo_unbound/results/max_hypo_composite_overnight_mild_gate_ablation_v1.json"
        )
        og_md = ROOT / str(
            og_cfg.get("summary_md_output") or "reports/max_hypo_composite_overnight_mild_gate_summary_v1.md"
        )
        steps.append(
            run_composite_overnight_mild_gate_ablation_sidecar(
                recipe=recipe,
                panel_csv=args.panel_csv,
                kospi_csv=args.kospi_csv,
                date_from=date_from,
                date_to=date_to,
                spotlight_dates=spotlight,
                out_path=og_out,
                md_path=og_md,
                dry_run=args.dry_run,
            )
        )

    if not args.skip_recommended_tier_manifest:
        rm_cfg = (
            recipe.get("max_hypo_recommended_tier_manifest")
            if isinstance(recipe.get("max_hypo_recommended_tier_manifest"), dict)
            else {}
        )
        rm_out = ROOT / str(
            rm_cfg.get("sidecar_output")
            or "experiments/max_hypo_unbound/results/max_hypo_recommended_tier_manifest_v1.json"
        )
        rm_md = ROOT / str(
            rm_cfg.get("summary_md_output") or "reports/max_hypo_recommended_tier_manifest_summary_v1.md"
        )
        steps.append(
            run_recommended_tier_manifest_sidecar(
                recipe=recipe,
                out_path=rm_out,
                md_path=rm_md,
                dry_run=args.dry_run,
            )
        )

    steps.append(
        shock_day_audit(
            recipe=recipe,
            kospi_csv=args.kospi_csv,
            panel_csv=args.panel_csv,
            spotlight_dates=spotlight,
        )
    )

    doc = build_report(recipe_path=args.recipe_json, steps=steps, dry_run=args.dry_run)
    if not args.dry_run:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"WROTE: {args.output.resolve()}")
        for st in steps:
            if st.get("step") == "multilens_backtest":
                print(
                    f"  multilens delta_max_hypo_minus_baseline="
                    f"{st.get('delta_max_hypo_minus_baseline_directional')}"
                )
            if st.get("step") == "walkforward" and st.get("mean_test_accuracy") is not None:
                print(f"  walkforward mean_test_accuracy={st.get('mean_test_accuracy')}")
            if st.get("step") == "shock_overlay_ablation":
                print(
                    f"  shock_ablation recommended_delta={st.get('recommended_delta_hit_rate')} "
                    f"best_sweep_delta={st.get('best_sweep_delta_hit_rate')}"
                )
            if st.get("step") == "bull_abstain_overlay_ablation":
                print(
                    f"  bull_abstain best_overlay={st.get('best_overlay')} "
                    f"best_delta={st.get('best_sweep_delta_hit_rate')} "
                    f"6/8={st.get('spotlight_6_8')}"
                )
            if st.get("step") == "shock_rebound_guard_ablation":
                print(
                    f"  rebound_guard recommended_delta={st.get('recommended_delta')} "
                    f"naive_-4.8_delta={st.get('naive_minus_4_8_delta')} "
                    f"6/8={st.get('spotlight_6_8_recommended')} "
                    f"6/9={st.get('spotlight_6_9_recommended')}"
                )
            if st.get("step") == "intraday_shock_proxy_ablation":
                print(
                    f"  intraday_oracle recommended_delta={st.get('oracle_recommended_delta')} "
                    f"composite recommended_delta={st.get('composite_recommended_delta')} "
                    f"6/8_oracle={st.get('spotlight_6_8_oracle')} "
                    f"6/8_composite={st.get('spotlight_6_8_composite')}"
                )
            if st.get("step") == "causal_open_limit_ablation":
                print(
                    f"  causal_tiers overnight_delta={st.get('tier_overnight_delta')} "
                    f"composite_delta={st.get('tier_composite_delta')} "
                    f"oracle_delta={st.get('tier_oracle_delta')} "
                    f"wf_mean_test_delta={st.get('wf_mean_test_delta')} "
                    f"oracle_minus_composite_pp={st.get('wf_oracle_minus_composite_gap_pp')}"
                )
            if st.get("step") == "causal_vol_range_proxy_ablation":
                print(
                    f"  vol_range composite_conservative_delta={st.get('composite_conservative_delta')} "
                    f"range_low_delta={st.get('range_low_delta')} "
                    f"vol_gated_delta={st.get('vol_gated_delta')} "
                    f"wf_conservative_test={st.get('wf_conservative_test_delta')} "
                    f"conservative_minus_aggressive_pp={st.get('wf_conservative_minus_aggressive_pp')} "
                    f"6/8_range={st.get('spotlight_6_8_range')}"
                )
            if st.get("step") == "causal_proxy_ensemble_holdout_ablation":
                print(
                    f"  ensemble_delta={st.get('ensemble_delta')} "
                    f"triple_delta={st.get('triple_ensemble_delta')} "
                    f"triple_minus_t7_pp={st.get('triple_minus_t7_pp')} "
                    f"range_delta={st.get('range_delta')} "
                    f"holdout_ensemble_delta={st.get('holdout_ensemble_delta')} "
                    f"holdout_triple_delta={st.get('holdout_triple_ensemble_delta')} "
                    f"range_wf_mean_test={st.get('range_wf_mean_test_delta')} "
                    f"6/8_ensemble={st.get('spotlight_6_8_ensemble')}"
                )
            if st.get("step") == "range_rebound_guard_refinement":
                print(
                    f"  range_rebound_rec guard={st.get('recommended_guard')} "
                    f"overnight_skip={st.get('recommended_overnight_skip')} "
                    f"delta={st.get('recommended_delta')} "
                    f"wf_fold1={st.get('wf_fold_1_test_delta')} "
                    f"fold1_remaining={st.get('fold1_regressions_remaining')} "
                    f"spotlight_safe={st.get('spotlight_safe')} "
                    f"md={st.get('md_output')}"
                )
            if st.get("step") == "prior_mild_range_conjunction_ablation":
                print(
                    f"  mild_range_conj t5_delta={st.get('t5_delta')} "
                    f"t9_delta={st.get('t9_recommended_delta')} "
                    f"t9_fold1={st.get('t9_fold1_test_delta')} "
                    f"regressions_fixed={st.get('regressions_fixed')} "
                    f"remaining_vs_t5={st.get('regressions_remaining_vs_t5')} "
                    f"spotlight_safe={st.get('spotlight_safe')} "
                    f"md={st.get('md_output')}"
                )
            if st.get("step") == "t9_ensemble_holdout_ablation":
                print(
                    f"  t9_ensemble t7_delta={st.get('t7_delta')} "
                    f"t10_delta={st.get('t10_delta')} "
                    f"t10_minus_t7_pp={st.get('t10_minus_t7_pp')} "
                    f"t11_minus_t8_pp={st.get('t11_minus_t8_pp')} "
                    f"holdout_t10={st.get('holdout_t10_delta')} "
                    f"regressions_fixed_vs_t7={st.get('regressions_fixed_vs_t7')} "
                    f"remaining_vs_t7={st.get('regressions_remaining_vs_t7')} "
                    f"spotlight_safe={st.get('spotlight_safe')} "
                    f"md={st.get('md_output')}"
                )
            if st.get("step") == "ensemble_soft_range_uplift_ablation":
                print(
                    f"  soft_range_uplift t7={st.get('t7_delta')} t10={st.get('t10_delta')} "
                    f"t12_rec={st.get('t12_recommended_delta')} cap={st.get('recommended_soft_cap')} "
                    f"vs_t7_pp={st.get('recommended_vs_t7_pp')} vs_t10_pp={st.get('recommended_vs_t10_pp')} "
                    f"remaining_vs_t7={st.get('regressions_remaining_vs_t7')} "
                    f"spotlight_safe={st.get('spotlight_safe')} md={st.get('md_output')}"
                )
            if st.get("step") == "composite_overnight_mild_gate_ablation":
                print(
                    f"  overnight_mild_gate t10={st.get('t10_delta')} t13={st.get('t13_delta')} "
                    f"t13_minus_t10_pp={st.get('t13_minus_t10_pp')} "
                    f"recommended={st.get('recommended_tier')} "
                    f"spotlight_safe={st.get('spotlight_safe')} md={st.get('md_output')}"
                )
            if st.get("step") == "recommended_tier_manifest":
                print(
                    f"  tier_manifest recommended={st.get('recommended_tier')} "
                    f"delta={st.get('recommended_delta')} vs_t7_pp={st.get('vs_t7_pp')} "
                    f"spotlight_safe={st.get('spotlight_safe')} md={st.get('md_output')}"
                )
            if st.get("step") == "shock_day_audit":
                for row in st.get("spotlight") or []:
                    print(
                        f"  spotlight {row.get('date')}: actual={row.get('actual_direction')} "
                        f"status={row.get('status')} preds={row.get('predictions')}"
                    )
    else:
        print(json.dumps(doc, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
