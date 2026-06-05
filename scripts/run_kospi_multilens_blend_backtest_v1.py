#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KOSPI multilens + 4AI blend backtest sweep [HYPO][research_only].

Compares v1 vs v2 weight/lens variants and 4AI overlay modes on historical
KRX weekdays with realized OHLCV (causal: predict session_date from prior data).
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_kospi_june2026_daily_prophecy_calendar_v1 import (  # noqa: E402
    _blend_direction,
    _logos_direction,
    _momentum_overlay,
    _read_json,
    _score_from_session_pillars,
)
from scripts.build_myeongni_jsonl_from_manseryeok_session_v1 import (  # noqa: E402
    _mapping_from_score,
)
from scripts.kospi_june2026_multilens_blend_v1 import (  # noqa: E402
    blend_v2_multilens,
    default_weights_v2,
    load_ensemble_kospi_per_date,
    load_static_lenses,
)
from scripts.kospi_june_4ai_prophecy_overlay_v1 import (  # noqa: E402
    FOUR_AI,
    _agent_vote_from_channels,
    _channel_consensus,
    _coordinator,
)

KOSPI_CSV = ROOT / "research/market_data/kospi_daily_external_yf.csv"
EVOLUTION_RULES = ROOT / "data/commander/kospi_june2026_prophecy_evolution_v1.json"
DEFAULT_PANEL = ROOT / "reports/btrack_session_myeongni_panel_252d_v1.csv"
DEFAULT_OUT = ROOT / "reports/kospi_multilens_blend_backtest_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_closes(csv_path: Path) -> dict[str, float]:
    out: dict[str, float] = {}
    with csv_path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            dk = str(row.get("Date", ""))[:10]
            if len(dk) != 10:
                continue
            try:
                out[dk] = float(row["Close"])
            except (KeyError, ValueError, TypeError):
                continue
    return out


def _load_panel(panel_csv: Path) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    with panel_csv.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            dk = str(row.get("session_local_date", ""))[:10]
            if dk:
                out[dk] = row
    return out


def _normalize_weights(weights: dict[str, float], keys: list[str]) -> dict[str, float]:
    w = {k: float(weights.get(k, 0.0)) for k in keys}
    total = sum(w.values())
    if total <= 0:
        return {k: round(1.0 / len(keys), 4) for k in keys}
    return {k: round(w[k] / total, 4) for k in keys}


def _variant_catalog(rules: dict[str, Any]) -> dict[str, dict[str, Any]]:
    v2_base = dict(rules.get("blend_weights_v2") or default_weights_v2())
    v2_keys = list(default_weights_v2().keys())

    def v2_variant(w_patch: dict[str, float], note: str) -> dict[str, Any]:
        w = deepcopy(v2_base)
        w.update(w_patch)
        return {
            "profile": "v2_multilens",
            "weights": _normalize_weights(w, v2_keys),
            "note": note,
        }

    session_heavy = deepcopy(v2_base)
    session_heavy["session_myeongni"] = 0.38
    session_heavy["momentum_overlay"] = 0.08

    field_mom = deepcopy(v2_base)
    field_mom["field_regime"] = 0.18
    field_mom["momentum_overlay"] = 0.18

    no_ens = deepcopy(v2_base)
    ens_w = float(no_ens.pop("ensemble_kospi_causal", 0.10))
    no_ens["session_myeongni"] = float(no_ens.get("session_myeongni", 0.22)) + ens_w * 0.5
    no_ens["macro"] = float(no_ens.get("macro", 0.10)) + ens_w * 0.5

    no_logos = deepcopy(v2_base)
    logos_w = float(no_logos.pop("logos_non_gating", 0.08))
    no_logos["sasang"] = float(no_logos.get("sasang", 0.12)) + logos_w

    lens3 = {k: 0.0 for k in v2_keys}
    lens3.update(
        {
            "session_myeongni": 0.30,
            "myeongni_independent": 0.22,
            "sasang": 0.24,
            "macro": 0.24,
        }
    )

    sess_mom_only = {k: 0.0 for k in v2_keys}
    sess_mom_only.update({"session_myeongni": 0.55, "momentum_overlay": 0.45})

    return {
        "v1_default": {
            "profile": "v1",
            "weights": dict(rules.get("blend_weights") or {"session_myeongni": 0.55, "momentum_overlay": 0.25, "logos_non_gating": 0.20}),
            "note": "session+mom+logos (legacy v1)",
        },
        "v2_default": v2_variant({}, "evolution blend_weights_v2 default"),
        "v2_session_heavy": v2_variant(session_heavy, "session_myeongni up"),
        "v2_field_momentum": v2_variant(field_mom, "field+momentum up"),
        "v2_no_ensemble": v2_variant(no_ens, "drop KOSPI causal ensemble"),
        "v2_no_logos": v2_variant(no_logos, "drop logos_non_gating"),
        "v2_lens3_heavy": v2_variant(lens3, "session+3 independent lenses only"),
        "v2_session_momentum_only": v2_variant(sess_mom_only, "session+momentum only"),
        "v2_session_light": v2_variant({"session_myeongni": 0.14}, "session_myeongni down"),
    }


def _coordinator_legacy(
    agents: list[dict[str, Any]],
    *,
    conflict_threshold: float = 0.55,
    mean_direction_threshold: float = 0.12,
) -> str:
    scores = [float(a.get("score") or 0.0) for a in agents]
    mean = sum(scores) / len(scores) if scores else 0.0
    var = sum((s - mean) ** 2 for s in scores) / len(scores) if scores else 0.0
    conflict = math.sqrt(var)
    bulls = sum(1 for a in agents if a.get("direction") == "bull")
    bears = sum(1 for a in agents if a.get("direction") == "bear")
    if conflict >= conflict_threshold or (bulls and bears):
        return "neutral"
    if mean > mean_direction_threshold:
        return "bull"
    if mean < -mean_direction_threshold:
        return "bear"
    return "neutral"


def _predict_v2(
    dk: str,
    *,
    panel_row: dict[str, str],
    closes: dict[str, float],
    static_lenses: dict[str, Any],
    ensemble_row: dict[str, Any] | None,
    weights: dict[str, float],
    blend_policy: dict[str, Any],
    neutral_band: float,
    four_ai_mode: str,
    coord_policy: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    pillars = {
        "year": str(panel_row.get("year_pillar") or ""),
        "month": str(panel_row.get("month_pillar") or ""),
        "day": str(panel_row.get("day_pillar") or ""),
        "hour": str(panel_row.get("hour_pillar") or ""),
    }
    session_score = _score_from_session_pillars(pillars)
    session_map = _mapping_from_score(session_score, neutral_band)
    mom_dir, _ = _momentum_overlay(closes, dk)
    pred_dir, _, detail = blend_v2_multilens(
        session_map=session_map,
        session_score=session_score,
        momentum_dir=mom_dir,
        static_lenses=static_lenses,
        ensemble_row=ensemble_row,
        weights=weights,
        neutral_band=neutral_band,
        blend_policy=blend_policy,
    )
    channels = detail.get("channels") if isinstance(detail.get("channels"), list) else []
    v2_dir = pred_dir

    if four_ai_mode == "none":
        return v2_dir, {"v2": v2_dir, "four_ai_mode": "none", "resolution_mode": detail.get("winner_resolution")}

    agents = [_agent_vote_from_channels(channels, aid) for aid in FOUR_AI]
    if four_ai_mode == "legacy_hold":
        f4 = _coordinator_legacy(
            agents,
            conflict_threshold=float(coord_policy.get("conflict_threshold", 0.55)),
            mean_direction_threshold=float(coord_policy.get("mean_direction_threshold", 0.12)),
        )
        return f4, {"v2": v2_dir, "four_ai_mode": "legacy_hold", "resolution_mode": "multilens_conflict_hold"}
    coord = _coordinator(
        agents,
        channels=channels,
        blend_policy=blend_policy,
        conflict_threshold=float(coord_policy.get("conflict_threshold", 0.75)),
        mean_direction_threshold=float(coord_policy.get("mean_direction_threshold", 0.12)),
    )
    return str(coord["coordinator_direction"]), {
        "v2": v2_dir,
        "four_ai_mode": "current",
        "resolution_mode": coord.get("resolution_mode"),
    }


def _predict_v1(
    dk: str,
    *,
    panel_row: dict[str, str],
    closes: dict[str, float],
    weights: dict[str, float],
    neutral_band: float,
    logos_dir: str,
) -> str:
    pillars = {
        "year": str(panel_row.get("year_pillar") or ""),
        "month": str(panel_row.get("month_pillar") or ""),
        "day": str(panel_row.get("day_pillar") or ""),
        "hour": str(panel_row.get("hour_pillar") or ""),
    }
    session_score = _score_from_session_pillars(pillars)
    session_map = _mapping_from_score(session_score, neutral_band)
    mom_dir, _ = _momentum_overlay(closes, dk)
    pred_dir, _, _ = _blend_direction(
        session_map=session_map,
        session_score=session_score,
        momentum_dir=mom_dir,
        logos_dir=logos_dir,
        weights=weights,
        neutral_band=neutral_band,
    )
    return pred_dir


def _direction_from_return(ret: float, neutral_bps: float) -> str:
    thr = neutral_bps / 10000.0
    if ret > thr:
        return "bull"
    if ret < -thr:
        return "bear"
    return "neutral"


def _outcome(pred: str, actual: str) -> str:
    if actual == "neutral" or pred == "neutral":
        return "NEUTRAL_DRAW"
    return "HIT" if pred == actual else "FAIL"


def _score_series(
    preds: dict[str, str],
    *,
    closes: dict[str, float],
    neutral_bps: float,
) -> dict[str, Any]:
    hits = fails = neutral = 0
    n = 0
    for dk, pred in sorted(preds.items()):
        older = sorted(d for d in closes if d < dk)
        if not older or dk not in closes:
            continue
        prior = closes[older[-1]]
        if prior == 0:
            continue
        ret = (closes[dk] - prior) / prior
        actual = _direction_from_return(ret, neutral_bps)
        oc = _outcome(pred, actual)
        n += 1
        if oc == "HIT":
            hits += 1
        elif oc == "FAIL":
            fails += 1
        else:
            neutral += 1
    n_dir = hits + fails
    return {
        "n_scored": n,
        "hit": hits,
        "fail": fails,
        "neutral_draw": neutral,
        "directional_hit_rate": round(hits / n_dir, 4) if n_dir else None,
        "soft_hit_rate": round((hits + 0.5 * neutral) / n, 4) if n else None,
    }


def run_backtest(
    *,
    panel_by_date: dict[str, dict[str, str]],
    closes: dict[str, float],
    date_from: str,
    date_to: str,
    rules: dict[str, Any],
    neutral_bps: float = 5.0,
) -> dict[str, Any]:
    neutral_band = float(rules.get("neutral_band", 0.06))
    blend_policy = dict(rules.get("blend_policy_v2") or {})
    coord_policy = dict(rules.get("four_ai_coordinator_policy") or {})
    logos_dir, _ = _logos_direction()
    static_lenses = load_static_lenses()

    eval_dates = sorted(d for d in panel_by_date if date_from <= d <= date_to)
    eval_dates = [d for d in eval_dates if d in closes]
    ensemble_by_date = load_ensemble_kospi_per_date(eval_dates)

    catalog = _variant_catalog(rules)
    four_ai_modes = ("none", "current", "legacy_hold")

    rows: list[dict[str, Any]] = []
    for variant_id, spec in catalog.items():
        profile = spec["profile"]
        weights = spec["weights"]
        for fam in ("base",):
            if profile == "v1":
                preds = {
                    dk: _predict_v1(
                        dk,
                        panel_row=panel_by_date[dk],
                        closes=closes,
                        weights=weights,
                        neutral_band=neutral_band,
                        logos_dir=logos_dir,
                    )
                    for dk in eval_dates
                }
                metrics = _score_series(preds, closes=closes, neutral_bps=neutral_bps)
                rows.append(
                    {
                        "variant_id": variant_id,
                        "family": "v1_no_4ai",
                        "profile": profile,
                        "four_ai_mode": "n/a",
                        "weights": weights,
                        "note": spec.get("note"),
                        "metrics": metrics,
                    }
                )
            else:
                for four_ai_mode in four_ai_modes:
                    preds = {}
                    diverge_from_v2 = 0
                    for dk in eval_dates:
                        pred, meta = _predict_v2(
                            dk,
                            panel_row=panel_by_date[dk],
                            closes=closes,
                            static_lenses=static_lenses,
                            ensemble_row=ensemble_by_date.get(dk),
                            weights=weights,
                            blend_policy=blend_policy,
                            neutral_band=neutral_band,
                            four_ai_mode=four_ai_mode,
                            coord_policy=coord_policy,
                        )
                        preds[dk] = pred
                        if meta.get("v2") != pred:
                            diverge_from_v2 += 1
                    metrics = _score_series(preds, closes=closes, neutral_bps=neutral_bps)
                    suffix = "" if four_ai_mode == "none" else f"_4ai_{four_ai_mode}"
                    rows.append(
                        {
                            "variant_id": f"{variant_id}{suffix}",
                            "family": "v2_multilens",
                            "profile": profile,
                            "four_ai_mode": four_ai_mode,
                            "weights": weights,
                            "note": spec.get("note"),
                            "diverge_from_v2_days": diverge_from_v2,
                            "metrics": metrics,
                        }
                    )

    def _rank_key(r: dict[str, Any]) -> tuple[float, float, int]:
        m = r.get("metrics") or {}
        soft = m.get("soft_hit_rate")
        direc = m.get("directional_hit_rate")
        return (
            float(soft) if soft is not None else -1.0,
            float(direc) if direc is not None else -1.0,
            int(m.get("n_scored") or 0),
        )

    ranked = sorted(rows, key=_rank_key, reverse=True)
    best = ranked[0] if ranked else None

    v2_none = [r for r in rows if r.get("four_ai_mode") == "none"]
    v2_4ai_current = [r for r in rows if r.get("four_ai_mode") == "current" and r["variant_id"].startswith("v2_default")]
    v2_4ai_legacy = [r for r in rows if r.get("four_ai_mode") == "legacy_hold" and r["variant_id"].startswith("v2_default")]

    return {
        "schema": "kospi_multilens_blend_backtest_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "track_wall": "no_track_a_live_auto_merge",
        "window": {"date_from": date_from, "date_to": date_to, "n_calendar_days": len(eval_dates)},
        "neutral_bps": neutral_bps,
        "static_lens_note": "Independent lenses + Field use latest artifact snapshot (not walk-forward refreshed).",
        "best_variant": best,
        "ranked_top5": ranked[:5],
        "comparison_highlights": {
            "best_overall": best.get("variant_id") if best else None,
            "best_v1": next((r for r in ranked if r.get("family") == "v1_no_4ai"), None),
            "best_v2_no_4ai": max(v2_none, key=_rank_key) if v2_none else None,
            "v2_default_no_4ai": next((r for r in v2_none if r["variant_id"] == "v2_default"), None),
            "v2_default_4ai_current": v2_4ai_current[0] if v2_4ai_current else None,
            "v2_default_4ai_legacy": v2_4ai_legacy[0] if v2_4ai_legacy else None,
        },
        "variants": rows,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--panel-csv", type=Path, default=DEFAULT_PANEL)
    ap.add_argument("--kospi-csv", type=Path, default=KOSPI_CSV)
    ap.add_argument("--date-from", default="2025-11-01")
    ap.add_argument("--date-to", default="2026-05-30")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    if not args.panel_csv.is_file():
        print(f"Missing panel: {args.panel_csv}", file=sys.stderr)
        return 2
    if not args.kospi_csv.is_file():
        print(f"Missing kospi csv: {args.kospi_csv}", file=sys.stderr)
        return 2

    rules = _read_json(EVOLUTION_RULES)
    panel = _load_panel(args.panel_csv)
    closes = _load_closes(args.kospi_csv)
    doc = run_backtest(
        panel_by_date=panel,
        closes=closes,
        date_from=args.date_from,
        date_to=args.date_to,
        rules=rules,
        neutral_bps=float(rules.get("neutral_bps", 5.0)),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    art = ROOT / "docs/final/artifacts/kospi_multilens_blend_backtest_latest.json"
    art.parent.mkdir(parents=True, exist_ok=True)
    art.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    best = doc.get("best_variant") or {}
    m = best.get("metrics") or {}
    print(
        f"WROTE: {args.output.resolve()} window={args.date_from}..{args.date_to} "
        f"n={doc['window']['n_calendar_days']} best={best.get('variant_id')} "
        f"soft={m.get('soft_hit_rate')} dir={m.get('directional_hit_rate')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
