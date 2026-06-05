#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""June KOSPI neutral prediction research bundle [HYPO][research_only].

1) Per-day neutral root-cause decomposition from sealed calendar blend detail.
2) blend_policy_v2 + neutral_band sweep (replay, no apply).
3) 4AI coordinator lock ON vs OFF counterfactual direction diff.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.kospi_june2026_multilens_blend_v1 import (  # noqa: E402
    blend_v2_multilens,
    load_ensemble_kospi_per_date,
    load_static_lenses,
)

DEFAULT_CAL = ROOT / "reports/kospi_202606_daily_prophecy_calendar_v1.json"
DEFAULT_CAL_FALLBACK = ROOT / "reports/kospi_june2026_daily_prophecy_calendar_v1.json"
DEFAULT_RULES = ROOT / "data/commander/kospi_june2026_prophecy_evolution_v1.json"
DEFAULT_EVAL = ROOT / "reports/kospi_june2026_daily_prophecy_eval_latest.json"
DEFAULT_OUT = ROOT / "reports/kospi_june2026_neutral_research_bundle_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _resolve_calendar_path(path: Path | None = None, *, year_month: str = "2026-06") -> Path:
    if path is not None and path.is_file():
        return path
    ym_tag = year_month.replace("-", "")
    candidates = [
        ROOT / f"reports/kospi_{ym_tag}_daily_prophecy_calendar_v1.json",
        DEFAULT_CAL,
        DEFAULT_CAL_FALLBACK,
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return path or DEFAULT_CAL


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


def _neutral_channel_drivers(channels: list[dict[str, Any]]) -> list[dict[str, Any]]:
    drivers: list[dict[str, Any]] = []
    for ch in channels:
        if str(ch.get("direction")) in ("neutral", "sideways"):
            drivers.append(
                {
                    "channel": ch.get("channel"),
                    "direction": ch.get("direction"),
                    "weight": round(float(ch.get("weight") or 0.0), 4),
                }
            )
    drivers.sort(key=lambda x: -float(x.get("weight") or 0))
    return drivers


def decompose_neutral_days(rows: list[dict[str, Any]]) -> dict[str, Any]:
    per_day: list[dict[str, Any]] = []
    reason_counts: Counter[str] = Counter()
    scored_dates = set()

    for row in rows:
        dk = str(row.get("session_date") or "")
        pred = str(row.get("predicted_direction") or "neutral")
        blend = row.get("blend") if isinstance(row.get("blend"), dict) else {}
        votes = blend.get("votes") if isinstance(blend.get("votes"), dict) else {}
        channels = blend.get("channels") if isinstance(blend.get("channels"), list) else []
        resolution = str(blend.get("winner_resolution") or "unknown")
        session_map = str(row.get("session_mapping_target") or "")

        entry: dict[str, Any] = {
            "session_date": dk,
            "predicted_direction": pred,
            "winner_resolution": resolution,
            "votes": votes,
            "blended_score": blend.get("blended_score"),
            "session_mapping_target": session_map,
            "session_direction_score": row.get("session_direction_score"),
        }

        if pred == "neutral":
            reason = resolution
            if session_map == "sideways" and votes.get("neutral", 0) >= max(votes.get("bull", 0), votes.get("bear", 0)):
                reason = "session_sideways_dominant"
            elif resolution == "directional_bull" or resolution == "directional_bear":
                reason = "score_band_demotion"
            reason_counts[reason] += 1
            entry["neutral_root_cause"] = reason
            entry["neutral_weight_drivers"] = _neutral_channel_drivers(channels)
            bull_w = float(votes.get("bull") or 0)
            bear_w = float(votes.get("bear") or 0)
            entry["directional_vote_gap"] = round(abs(bull_w - bear_w), 4)
        per_day.append(entry)

    n_neutral = sum(1 for r in rows if r.get("predicted_direction") == "neutral")
    return {
        "n_trading_days": len(rows),
        "n_neutral_predictions": n_neutral,
        "n_directional_predictions": len(rows) - n_neutral,
        "neutral_rate": round(n_neutral / len(rows), 4) if rows else None,
        "root_cause_counts": dict(reason_counts),
        "per_day": per_day,
        "scored_dates": sorted(scored_dates),
    }


def sweep_blend_policy(
    rows: list[dict[str, Any]],
    *,
    static_lenses: dict[str, Any],
    ensemble_by_date: dict[str, dict[str, Any]],
    base_policy: dict[str, Any],
    base_neutral_band: float,
    base_weights: dict[str, float],
) -> list[dict[str, Any]]:
    neutral_bands = [0.04, 0.06, 0.08, 0.10]
    min_weights = [0.24, 0.28, 0.32]
    margins = [1.08, 1.12, 1.16]
    results: list[dict[str, Any]] = []

    for nb in neutral_bands:
        for mw in min_weights:
            for mg in margins:
                policy = {
                    **base_policy,
                    "directional_winner_min_weight": mw,
                    "directional_margin_ratio": mg,
                    "prefer_directional_over_neutral": True,
                    "require_directional_plurality": True,
                }
                counts: Counter[str] = Counter()
                diffs_vs_active: list[str] = []
                for row in rows:
                    dk = str(row.get("session_date") or "")
                    session_map = str(row.get("session_mapping_target") or "sideways")
                    session_score = float(row.get("session_direction_score") or 0.0)
                    mom_dir = _momentum_from_row(row)
                    weights = (row.get("blend") or {}).get("weights") or base_weights
                    pred, _, detail = blend_v2_multilens(
                        session_map=session_map,
                        session_score=session_score,
                        momentum_dir=mom_dir,
                        static_lenses=static_lenses,
                        ensemble_row=ensemble_by_date.get(dk),
                        weights=weights,
                        neutral_band=nb,
                        blend_policy=policy,
                    )
                    counts[pred] += 1
                    if pred != str(row.get("predicted_direction") or ""):
                        diffs_vs_active.append(dk)
                results.append(
                    {
                        "neutral_band": nb,
                        "directional_winner_min_weight": mw,
                        "directional_margin_ratio": mg,
                        "direction_counts": dict(counts),
                        "n_neutral": counts.get("neutral", 0),
                        "n_diff_vs_active_calendar": len(diffs_vs_active),
                        "diff_dates": diffs_vs_active[:12],
                    }
                )
    results.sort(key=lambda x: (x["n_neutral"], x["n_diff_vs_active_calendar"]))
    return results


def four_ai_counterfactual(
    calendar: dict[str, Any],
    *,
    evolution_path: Path,
    eval_doc: dict[str, Any] | None,
) -> dict[str, Any]:
    import scripts.kospi_june_4ai_prophecy_overlay_v1 as overlay

    rules = _read_json(evolution_path)
    blend_policy = rules.get("blend_policy_v2") if isinstance(rules.get("blend_policy_v2"), dict) else {}
    coord_base = rules.get("four_ai_coordinator_policy") if isinstance(rules.get("four_ai_coordinator_policy"), dict) else {}

    locked_pol = {**coord_base, "lock_coordinator_to_v2_calendar": True}
    unlocked_pol = {**coord_base, "lock_coordinator_to_v2_calendar": False}

    locked_doc = overlay.build_4ai_report(
        calendar,
        eval_doc=eval_doc,
        blend_policy=blend_policy,
        coordinator_policy=locked_pol,
    )
    unlocked_doc = overlay.build_4ai_report(
        calendar,
        eval_doc=eval_doc,
        blend_policy=blend_policy,
        coordinator_policy=unlocked_pol,
    )

    locked_by_date = {str(r["session_date"]): r for r in locked_doc.get("rows") or []}
    unlocked_by_date = {str(r["session_date"]): r for r in unlocked_doc.get("rows") or []}

    diffs: list[dict[str, Any]] = []
    for dk in sorted(unlocked_by_date.keys()):
        u = unlocked_by_date[dk]
        l = locked_by_date.get(dk) or {}
        u_dir = str(u.get("four_ai_direction") or "neutral")
        l_dir = str(l.get("four_ai_direction") or "neutral")
        v2_dir = str(u.get("v2_multilens_direction") or "neutral")
        if u_dir != l_dir:
            diffs.append(
                {
                    "session_date": dk,
                    "v2_direction": v2_dir,
                    "four_ai_unlocked": u_dir,
                    "four_ai_locked": l_dir,
                    "unlocked_resolution_mode": (u.get("absolute_balance") or {}).get("resolution_mode"),
                    "would_change_v2_calendar": u_dir != v2_dir,
                }
            )

    unlocked_counts = Counter(str(r.get("four_ai_direction") or "neutral") for r in unlocked_doc.get("rows") or [])
    locked_counts = Counter(str(r.get("four_ai_direction") or "neutral") for r in locked_doc.get("rows") or [])
    v2_counts = Counter(str(r.get("predicted_direction") or "neutral") for r in calendar.get("rows") or [])

    return {
        "lock_coordinator_to_v2_calendar": {
            "true": {
                "direction_counts": dict(locked_counts),
                "coordinator_kpi": locked_doc.get("coordinator_kpi"),
            },
            "false": {
                "direction_counts": dict(unlocked_counts),
                "coordinator_kpi": unlocked_doc.get("coordinator_kpi"),
            },
        },
        "v2_calendar_direction_counts": dict(v2_counts),
        "n_direction_diffs_lock_vs_unlock": len(diffs),
        "diff_rows": diffs,
        "n_unlocked_would_change_v2": sum(1 for d in diffs if d.get("would_change_v2_calendar")),
    }


def build_bundle(
    *,
    calendar: dict[str, Any],
    rules: dict[str, Any],
    eval_doc: dict[str, Any] | None,
    evolution_path: Path,
    calendar_path: Path,
) -> dict[str, Any]:
    rows = calendar.get("rows") if isinstance(calendar.get("rows"), list) else []
    trading_days = [str(r.get("session_date")) for r in rows if r.get("session_date")]
    static_lenses = load_static_lenses()
    ensemble_by_date = load_ensemble_kospi_per_date(trading_days)

    decomposition = decompose_neutral_days(rows)
    if eval_doc:
        decomposition["forward_eval"] = {
            "as_of_kst": eval_doc.get("as_of_kst"),
            "n_scored": eval_doc.get("n_scored"),
            "metrics": eval_doc.get("metrics"),
            "missing_ohlcv_trading_days": eval_doc.get("missing_ohlcv_trading_days"),
        }
    base_policy = rules.get("blend_policy_v2") if isinstance(rules.get("blend_policy_v2"), dict) else {}
    base_nb = float(rules.get("neutral_band", 0.06))
    base_weights = calendar.get("blend_weights_applied") if isinstance(calendar.get("blend_weights_applied"), dict) else {}

    sweep = sweep_blend_policy(
        rows,
        static_lenses=static_lenses,
        ensemble_by_date=ensemble_by_date,
        base_policy=base_policy,
        base_neutral_band=base_nb,
        base_weights=base_weights,
    )
    best_sweep = min(sweep, key=lambda x: x["n_neutral"]) if sweep else None
    counterfactual = four_ai_counterfactual(calendar, evolution_path=evolution_path, eval_doc=eval_doc)

    findings: list[str] = []
    rc = decomposition.get("root_cause_counts") or {}
    if rc.get("neutral_plurality", 0) + rc.get("session_sideways_dominant", 0) >= decomposition.get("n_neutral_predictions", 0) // 2:
        findings.append("neutral 다수는 채널 가중 plurality·세션 sideways — neutral_bps 스윕만으로는 HIT/FAIL 안 생김")
    if best_sweep and best_sweep["n_neutral"] < decomposition.get("n_neutral_predictions", 0):
        findings.append(
            f"policy sweep 최소 neutral={best_sweep['n_neutral']} "
            f"(nb={best_sweep['neutral_band']}, min_w={best_sweep['directional_winner_min_weight']}) "
            "— evolution dry-run 후보만"
        )
    else:
        findings.append("policy sweep으로도 June neutral 9일 구조 크게 안 줄음 — 채널 방향 입력 쪽 연구 우선")
    if counterfactual.get("n_unlocked_would_change_v2", 0) > 0:
        findings.append(
            f"4AI lock OFF 시 {counterfactual['n_unlocked_would_change_v2']}일 v2와 불일치 — "
            "백테스트 4AI 이득은 published calendar와 분리됨"
        )
    else:
        findings.append("4AI unlock도 v2 calendar 방향 변경 없음 — overlay 이득은 해설·밴드층")

    return {
        "schema": "kospi_june2026_neutral_research_bundle_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "auto_apply": False,
        "year_month": calendar.get("year_month") or "2026-06",
        "active_candidate_id": calendar.get("weights_candidate_id") or rules.get("last_candidate_apply_id"),
        "calendar_path": str(calendar_path.relative_to(ROOT)).replace("\\", "/")
        if calendar_path.is_relative_to(ROOT)
        else str(calendar_path).replace("\\", "/"),
        "neutral_decomposition": decomposition,
        "policy_sweep": {
            "grid_size": len(sweep),
            "active_neutral_band": base_nb,
            "active_blend_policy_v2": base_policy,
            "best_lowest_neutral": best_sweep,
            "top5_lowest_neutral": sweep[:5],
        },
        "four_ai_counterfactual": counterfactual,
        "key_findings_ko": findings,
        "recommended_next_ko": "June n≥15 포워드 누적 후 unlock diff·sweep 결과와 soft HR 교차검증. apply 금지.",
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--year-month", type=str, default="2026-06")
    ap.add_argument("--calendar-json", type=Path, default=None)
    ap.add_argument("--rules-json", type=Path, default=DEFAULT_RULES)
    ap.add_argument("--eval-json", type=Path, default=DEFAULT_EVAL)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    cal_path = _resolve_calendar_path(args.calendar_json, year_month=args.year_month)
    calendar = _read_json(cal_path)
    if not calendar.get("rows"):
        raise SystemExit(f"Missing calendar rows: {cal_path}")

    rules = _read_json(args.rules_json)
    eval_doc = _read_json(args.eval_json) if args.eval_json.is_file() else None

    doc = build_bundle(
        calendar=calendar,
        rules=rules,
        eval_doc=eval_doc,
        evolution_path=args.rules_json,
        calendar_path=cal_path,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    decomp = doc["neutral_decomposition"]
    cf = doc["four_ai_counterfactual"]
    print(
        f"WROTE: {args.output.resolve()} "
        f"neutral={decomp.get('n_neutral_predictions')}/{decomp.get('n_trading_days')} "
        f"4ai_unlock_diffs={cf.get('n_direction_diffs_lock_vs_unlock')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
