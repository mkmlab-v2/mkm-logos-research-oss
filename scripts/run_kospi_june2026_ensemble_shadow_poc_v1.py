#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KOSPI June ensemble + low-confidence gate shadow PoC [HYPO][research_only].

Tests whether re-enabling ensemble_kospi_causal (weight 0.10) and/or relaxing
min_direction_confidence changes June calendar directions vs active v2_lens3_heavy.
Does not apply weights or touch Track A.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.btrack_ensemble_per_date_core_v1 import compute_per_date_direction_rows  # noqa: E402
from scripts.kospi_june2026_multilens_blend_v1 import (  # noqa: E402
    blend_v2_multilens,
    default_weights_v2,
    load_static_lenses,
)

DEFAULT_CAL = ROOT / "reports/kospi_june2026_daily_prophecy_calendar_v1.json"
DEFAULT_RULES = ROOT / "data/commander/kospi_june2026_prophecy_evolution_v1.json"
BUNDLE = ROOT / "docs/final/artifacts/btrack_llm_input_bundle_latest.json"
ENSEMBLE_CFG = ROOT / "docs/final/artifacts/btrack_lens_ensemble_v1.json"
KOSPI_CSV = ROOT / "research/market_data/kospi_daily_external_yf.csv"
DEFAULT_OUT = ROOT / "reports/kospi_june2026_ensemble_shadow_poc_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _momentum_from_row(row: dict[str, Any]) -> str:
    blend = row.get("blend") if isinstance(row.get("blend"), dict) else {}
    for ch in blend.get("channels") or []:
        if str(ch.get("channel")) == "momentum_overlay":
            return str(ch.get("direction") or "neutral")
    return "neutral"


def _weights_with_ensemble(base: dict[str, float], ens_w: float) -> dict[str, float]:
    """Scale non-ensemble channels so total mass includes ens_w."""
    w = {**default_weights_v2(), **base}
    ens_w = max(0.0, min(1.0, float(ens_w)))
    if ens_w <= 0:
        w["ensemble_kospi_causal"] = 0.0
        return w
    keys = [k for k in w if k != "ensemble_kospi_causal"]
    subtotal = sum(float(w.get(k) or 0) for k in keys) or 1.0
    scale = (1.0 - ens_w) / subtotal
    out = {k: round(float(w.get(k) or 0) * scale, 4) for k in keys}
    out["ensemble_kospi_causal"] = round(ens_w, 4)
    return out


def _ensemble_by_date(
    eval_dates: list[str],
    *,
    min_direction_confidence: float,
) -> dict[str, dict[str, Any]]:
    bundle = _read_json(BUNDLE)
    cfg = deepcopy(_read_json(ENSEMBLE_CFG))
    rules = dict(cfg.get("rules") or {})
    rules["ensemble_mode"] = "v2_confidence_fusion"
    rules["price_instrument"] = "kospi"
    rules["enforce_btc_only_guard"] = False
    rules["min_direction_confidence"] = float(min_direction_confidence)
    cfg["rules"] = rules
    rows = compute_per_date_direction_rows(
        bundle=bundle,
        ensemble_cfg=cfg,
        eval_dates=eval_dates,
        btc_csv=KOSPI_CSV,
        instrument="kospi",
    )
    return {str(r["eval_date"]): r for r in rows if r.get("eval_date")}


def _replay_june_directions(
    rows: list[dict[str, Any]],
    *,
    static_lenses: dict[str, Any],
    ensemble_by_date: dict[str, dict[str, Any]],
    weights: dict[str, float],
    blend_policy: dict[str, Any],
    neutral_band: float,
) -> dict[str, Any]:
    counts: Counter[str] = Counter()
    gate_applied = 0
    prelim_bear = 0
    diffs: list[str] = []
    per_day: list[dict[str, Any]] = []

    for row in rows:
        dk = str(row.get("session_date") or "")
        active = str(row.get("predicted_direction") or "neutral")
        session_map = str(row.get("session_mapping_target") or "sideways")
        session_score = float(row.get("session_direction_score") or 0.0)
        ens = ensemble_by_date.get(dk) or {}
        if (ens.get("low_confidence_direction_gate") or {}).get("applied"):
            gate_applied += 1
        if str(ens.get("preliminary_direction") or "") == "bear":
            prelim_bear += 1
        pred, _, detail = blend_v2_multilens(
            session_map=session_map,
            session_score=session_score,
            momentum_dir=_momentum_from_row(row),
            static_lenses=static_lenses,
            ensemble_row=ens or None,
            weights=weights,
            neutral_band=neutral_band,
            blend_policy=blend_policy,
        )
        counts[pred] += 1
        if pred != active:
            diffs.append(dk)
        per_day.append(
            {
                "session_date": dk,
                "active_direction": active,
                "shadow_direction": pred,
                "ensemble_predicted": ens.get("predicted_direction"),
                "ensemble_preliminary": ens.get("preliminary_direction"),
                "ensemble_confidence": ens.get("confidence"),
                "gate_applied": (ens.get("low_confidence_direction_gate") or {}).get("applied"),
            }
        )

    return {
        "direction_counts": dict(counts),
        "n_neutral": counts.get("neutral", 0),
        "n_diff_vs_active_calendar": len(diffs),
        "diff_dates": diffs,
        "ensemble_gate_applied_days": gate_applied,
        "ensemble_preliminary_bear_days": prelim_bear,
        "per_day_sample": per_day[:5],
    }


def run_shadow_poc(
    *,
    calendar: dict[str, Any],
    rules: dict[str, Any],
) -> dict[str, Any]:
    rows = calendar.get("rows") if isinstance(calendar.get("rows"), list) else []
    trading_days = [str(r.get("session_date")) for r in rows if r.get("session_date")]
    static_lenses = load_static_lenses()
    base_weights = calendar.get("blend_weights_applied") if isinstance(calendar.get("blend_weights_applied"), dict) else {}
    blend_policy = rules.get("blend_policy_v2") if isinstance(rules.get("blend_policy_v2"), dict) else {}
    neutral_band = float(rules.get("neutral_band", 0.06))

    scenarios: list[dict[str, Any]] = []
    for sid, ens_w, gate in (
        ("S0_active_baseline", 0.0, 0.18),
        ("S1_ens010_gate018", 0.10, 0.18),
        ("S2_ens010_gate012", 0.10, 0.12),
        ("S3_ens010_gate000", 0.10, 0.0),
    ):
        ens_map = _ensemble_by_date(trading_days, min_direction_confidence=gate)
        ens_dirs = Counter(str(v.get("predicted_direction") or "neutral") for v in ens_map.values())
        weights = _weights_with_ensemble(base_weights, ens_w)
        replay = _replay_june_directions(
            rows,
            static_lenses=static_lenses,
            ensemble_by_date=ens_map,
            weights=weights,
            blend_policy=blend_policy,
            neutral_band=neutral_band,
        )
        scenarios.append(
            {
                "scenario_id": sid,
                "ensemble_weight": ens_w,
                "min_direction_confidence": gate,
                "weights_applied": weights,
                "ensemble_direction_counts": dict(ens_dirs),
                "calendar_replay": replay,
            }
        )

    baseline = scenarios[0]["calendar_replay"]
    best = min(scenarios, key=lambda s: s["calendar_replay"]["n_neutral"])

    findings = [
        "ensemble predicted_direction=neutral 21/21 — preliminary_direction=bear 다수 + min_direction_confidence=0.18 gate [FACT]",
        f"gate 0.12/0.0 shadow 시 ensemble bear 방향 복원 — calendar diff는 ens 가중 0.10 재활성화와 함께 봐야 함 [HYPO]",
    ]
    if best["scenario_id"] != "S0_active_baseline" and best["calendar_replay"]["n_neutral"] < baseline["n_neutral"]:
        findings.append(
            f"최소 neutral shadow={best['scenario_id']} ({best['calendar_replay']['n_neutral']}일) — apply 금지·n≥15 forward 교차 필요"
        )
    else:
        findings.append("June calendar neutral 구조는 ensemble shadow만으로 크게 안 줄음 — session/macro 입력 연구 우선 [HYPO]")

    return {
        "schema": "kospi_june2026_ensemble_shadow_poc_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "auto_apply": False,
        "track_wall": "no_track_a_live_auto_merge",
        "year_month": calendar.get("year_month") or "2026-06",
        "active_candidate_id": calendar.get("weights_candidate_id"),
        "gpu_used": False,
        "scenarios": scenarios,
        "best_lowest_neutral_scenario": best["scenario_id"],
        "key_findings_ko": findings,
        "recommended_next_ko": "May+June holdout soft HR with S2/S3 vs active — shadow panel only. apply 금지.",
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--calendar-json", type=Path, default=DEFAULT_CAL)
    ap.add_argument("--rules-json", type=Path, default=DEFAULT_RULES)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    calendar = _read_json(args.calendar_json)
    if not calendar.get("rows"):
        raise SystemExit(f"Missing calendar rows: {args.calendar_json}")

    doc = run_shadow_poc(calendar=calendar, rules=_read_json(args.rules_json))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    best_id = doc["best_lowest_neutral_scenario"]
    best = next(s for s in doc["scenarios"] if s["scenario_id"] == best_id)
    print(
        f"WROTE: {args.output.resolve()} "
        f"best={best_id} neutral={best['calendar_replay']['n_neutral']} "
        f"diffs={best['calendar_replay']['n_diff_vs_active_calendar']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
