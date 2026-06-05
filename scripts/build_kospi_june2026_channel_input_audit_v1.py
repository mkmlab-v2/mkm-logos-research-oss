#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""June KOSPI channel direction input audit [HYPO][research_only].

Static lens freshness, neutral-day vote anatomy, scored-day counterfactuals
(per-date JSONL replay when available, 4AI unlock soft on forward sample).
No calendar apply.
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

from scripts.eval_kospi_june2026_daily_prophecy_v1 import _outcome  # noqa: E402
from scripts.kospi_june2026_multilens_blend_v1 import (  # noqa: E402
    blend_v2_multilens,
    load_ensemble_kospi_per_date,
    load_static_lenses,
)
from scripts.kospi_lens_per_date_static_v1 import (  # noqa: E402
    load_lens_jsonl_by_day,
    static_lenses_for_eval_date,
)

DEFAULT_CAL = ROOT / "reports/kospi_202606_daily_prophecy_calendar_v1.json"
DEFAULT_CAL_FALLBACK = ROOT / "reports/kospi_june2026_daily_prophecy_calendar_v1.json"
DEFAULT_RULES = ROOT / "data/commander/kospi_june2026_prophecy_evolution_v1.json"
DEFAULT_EVAL = ROOT / "reports/kospi_june2026_daily_prophecy_eval_latest.json"
DEFAULT_NEUTRAL = ROOT / "reports/kospi_june2026_neutral_research_bundle_latest.json"
DEFAULT_OUT = ROOT / "reports/kospi_june2026_channel_input_audit_latest.json"
DEFAULT_MYEONGNI_JSONL = ROOT / "data/myeongni/myeongni_16_state_experiment_v1.manseryeok_session_30y_v1.jsonl"
DEFAULT_SASANG_JSONL = ROOT / "data/sasang/sasang_dynamics_regime_mapping_v1.manseryeok_session_30y_v1.jsonl"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _resolve_calendar_path(path: Path | None = None, *, year_month: str = "2026-06") -> Path:
    if path is not None and path.is_file():
        return path
    ym_tag = year_month.replace("-", "")
    for candidate in (
        ROOT / f"reports/kospi_{ym_tag}_daily_prophecy_calendar_v1.json",
        DEFAULT_CAL,
        DEFAULT_CAL_FALLBACK,
    ):
        if candidate.is_file():
            return candidate
    return path or DEFAULT_CAL


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _momentum_from_row(row: dict[str, Any]) -> str:
    blend = row.get("blend") if isinstance(row.get("blend"), dict) else {}
    for ch in blend.get("channels") or []:
        if str(ch.get("channel")) == "momentum_overlay":
            return str(ch.get("direction") or "neutral")
    return str(blend.get("momentum_direction") or "neutral")


def _soft_from_outcomes(outcomes: list[str]) -> float | None:
    if not outcomes:
        return None
    total = 0.0
    for o in outcomes:
        if o == "HIT":
            total += 1.0
        elif o == "NEUTRAL_DRAW":
            total += 0.5
    return round(total / len(outcomes), 4)


def _lens_freshness(static: dict[str, Any]) -> list[dict[str, Any]]:
    keys = (
        ("myeongni_independent", "myeongni_independent"),
        ("sasang", "sasang"),
        ("macro", "macro"),
        ("logos", "logos"),
        ("field_regime", "field_regime"),
    )
    rows: list[dict[str, Any]] = []
    for channel, key in keys:
        lens = static.get(key) or {}
        art_path = lens.get("path")
        ts = None
        row_ts = None
        if art_path:
            p = Path(str(art_path))
            if not p.is_absolute():
                p = ROOT / p
            doc = _read_json(p)
            ts = doc.get("ts_utc")
            prov = doc.get("provenance") if isinstance(doc.get("provenance"), dict) else {}
            row_ts = prov.get("row_ts_utc") or doc.get("row_ts_utc")
        rows.append(
            {
                "channel": channel,
                "direction": lens.get("direction"),
                "score": lens.get("score"),
                "loaded": lens.get("loaded"),
                "artifact_ts_utc": ts,
                "source_row_ts_utc": row_ts,
                "path": art_path,
            }
        )
    return rows


def _replay_row(
    row: dict[str, Any],
    *,
    static_lenses: dict[str, Any],
    ensemble_by_date: dict[str, dict[str, Any]],
    weights: dict[str, float],
    neutral_band: float,
    blend_policy: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    dk = str(row.get("session_date"))
    pred, _, detail = blend_v2_multilens(
        session_map=str(row.get("session_mapping_target") or "sideways"),
        session_score=float(row.get("session_direction_score") or 0.0),
        momentum_dir=_momentum_from_row(row),
        static_lenses=static_lenses,
        ensemble_row=ensemble_by_date.get(dk),
        weights=weights,
        neutral_band=neutral_band,
        blend_policy=blend_policy,
    )
    return pred, detail


def _neutral_vote_anatomy(row: dict[str, Any]) -> dict[str, Any]:
    blend = row.get("blend") if isinstance(row.get("blend"), dict) else {}
    votes = blend.get("votes") if isinstance(blend.get("votes"), dict) else {}
    bull = float(votes.get("bull") or 0)
    bear = float(votes.get("bear") or 0)
    neutral = float(votes.get("neutral") or 0)
    return {
        "session_date": row.get("session_date"),
        "session_mapping_target": row.get("session_mapping_target"),
        "votes": votes,
        "winner_resolution": blend.get("winner_resolution"),
        "gap_bull_minus_bear": round(bull - bear, 4),
        "gap_directional_minus_neutral": round(max(bull, bear) - neutral, 4),
        "would_bull_win_if_neutral_band_only": bull > bear and bull > neutral,
        "would_bear_win_if_neutral_band_only": bear > bull and bear > neutral,
    }


def build_audit(
    *,
    calendar: dict[str, Any],
    rules: dict[str, Any],
    eval_doc: dict[str, Any] | None,
    neutral_bundle: dict[str, Any] | None,
    myeongni_jsonl: Path,
    sasang_jsonl: Path,
    calendar_path: Path,
) -> dict[str, Any]:
    rows = calendar.get("rows") if isinstance(calendar.get("rows"), list) else []
    trading_days = [str(r.get("session_date")) for r in rows if r.get("session_date")]
    weights = calendar.get("blend_weights_applied") if isinstance(calendar.get("blend_weights_applied"), dict) else {}
    neutral_band = float(rules.get("neutral_band", 0.06))
    blend_policy = rules.get("blend_policy_v2") if isinstance(rules.get("blend_policy_v2"), dict) else {}

    static_global = load_static_lenses()
    ensemble_by_date = load_ensemble_kospi_per_date(trading_days)
    freshness = _lens_freshness(static_global)

    per_date_available = myeongni_jsonl.is_file() and sasang_jsonl.is_file()
    my_by, sa_by, jsonl_meta = ({}, {}, {"available": False})
    if per_date_available:
        my_by, sa_by, jsonl_meta = load_lens_jsonl_by_day(myeongni_jsonl, sasang_jsonl)
        jsonl_meta["available"] = True

    replay_diffs: list[dict[str, Any]] = []
    for row in rows:
        dk = str(row.get("session_date"))
        active = str(row.get("predicted_direction") or "neutral")
        if per_date_available:
            per_static = static_lenses_for_eval_date(
                dk, sasang_by_day=sa_by, myeongni_by_day=my_by, baseline=static_global
            )
            per_pred, per_detail = _replay_row(
                row,
                static_lenses=per_static,
                ensemble_by_date=ensemble_by_date,
                weights=weights,
                neutral_band=neutral_band,
                blend_policy=blend_policy,
            )
            if per_pred != active:
                replay_diffs.append(
                    {
                        "session_date": dk,
                        "active": active,
                        "per_date_lens_replay": per_pred,
                        "per_date_votes": per_detail.get("votes"),
                    }
                )

    neutral_anatomy = [
        _neutral_vote_anatomy(r) for r in rows if str(r.get("predicted_direction")) == "neutral"
    ]

    scored_rows = (eval_doc or {}).get("rows") or []
    scored_dates = {str(r.get("session_date")) for r in scored_rows if r.get("session_date")}
    actual_by_date = {str(r.get("session_date")): str(r.get("actual_direction")) for r in scored_rows}

    unlock_map: dict[str, str] = {}
    cf = (neutral_bundle or {}).get("four_ai_counterfactual") if isinstance(neutral_bundle, dict) else {}
    for diff in cf.get("diff_rows") or []:
        if isinstance(diff, dict) and diff.get("session_date"):
            unlock_map[str(diff["session_date"])] = str(diff.get("four_ai_unlocked") or "neutral")

    scored_counterfactuals: list[dict[str, Any]] = []
    active_outcomes: list[str] = []
    unlock_outcomes: list[str] = []
    per_date_outcomes: list[str] = []

    for row in scored_rows:
        dk = str(row.get("session_date"))
        actual = actual_by_date.get(dk, "neutral")
        active_dir = str(row.get("predicted_direction") or "neutral")
        active_oc = str(row.get("outcome") or _outcome(active_dir, actual))
        active_outcomes.append(active_oc)

        unlock_dir = unlock_map.get(dk, active_dir)
        unlock_oc = _outcome(unlock_dir, actual)
        unlock_outcomes.append(unlock_oc)

        per_dir = active_dir
        if per_date_available:
            cal_row = next((r for r in rows if str(r.get("session_date")) == dk), None)
            if cal_row:
                per_static = static_lenses_for_eval_date(
                    dk, sasang_by_day=sa_by, myeongni_by_day=my_by, baseline=static_global
                )
                per_dir, _ = _replay_row(
                    cal_row,
                    static_lenses=per_static,
                    ensemble_by_date=ensemble_by_date,
                    weights=weights,
                    neutral_band=neutral_band,
                    blend_policy=blend_policy,
                )
        per_date_outcomes.append(_outcome(per_dir, actual))

        scored_counterfactuals.append(
            {
                "session_date": dk,
                "actual_direction": actual,
                "active_direction": active_dir,
                "active_outcome": active_oc,
                "four_ai_unlock_direction": unlock_dir,
                "four_ai_unlock_outcome": unlock_oc,
                "per_date_lens_direction": per_dir if per_date_available else None,
                "per_date_lens_outcome": _outcome(per_dir, actual) if per_date_available else None,
            }
        )

    findings: list[str] = []
    stale = [f for f in freshness if f.get("source_row_ts_utc") and str(f["source_row_ts_utc"]) < "2026-06-01"]
    if stale:
        findings.append(
            "독립 렌즈 artifact source_row가 6월 이전 — June 채널 입력은 글로벌 스냅샷 고정 [HYPO]"
        )
    neutral_floor = sum(1 for a in neutral_anatomy if float((a.get("votes") or {}).get("neutral") or 0) >= 0.46)
    if neutral_floor >= len(neutral_anatomy) // 2:
        findings.append(
            f"neutral {len(neutral_anatomy)}일 중 {neutral_floor}일 neutral vote≥0.46 — "
            "session sideways+macro/myeongni neutral 가중이 바닥"
        )
    if not per_date_available:
        findings.append("per-date myeongni/sasang JSONL 없음 — replay diff 생략, static snapshot만")
    elif not replay_diffs:
        findings.append("per-date JSONL replay도 June active calendar 방향 diff 0 — 입력 stale보다 blend policy 구조")
    if unlock_outcomes and _soft_from_outcomes(unlock_outcomes) != _soft_from_outcomes(active_outcomes):
        findings.append(
            f"4AI unlock scored soft {_soft_from_outcomes(unlock_outcomes)} vs active "
            f"{_soft_from_outcomes(active_outcomes)} — overlay만, v2 apply 아님"
        )

    return {
        "schema": "kospi_june2026_channel_input_audit_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "auto_apply": False,
        "year_month": calendar.get("year_month") or "2026-06",
        "calendar_path": _rel(calendar_path),
        "static_lens_freshness": freshness,
        "per_date_jsonl": jsonl_meta,
        "neutral_vote_anatomy": neutral_anatomy,
        "per_date_replay_diffs": replay_diffs,
        "scored_day_counterfactuals": {
            "n_scored": len(scored_counterfactuals),
            "active_soft_hit_rate": _soft_from_outcomes(active_outcomes),
            "four_ai_unlock_soft_hit_rate": _soft_from_outcomes(unlock_outcomes),
            "per_date_lens_soft_hit_rate": _soft_from_outcomes(per_date_outcomes) if per_date_available else None,
            "days": scored_counterfactuals,
        },
        "key_findings_ko": findings,
        "recommended_next_ko": "n≥7 scored 후 unlock·per-date soft 재계산; macro/myeongni 일일 갱신 PoC는 JSONL·체인 별도.",
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--year-month", default="2026-06")
    ap.add_argument("--calendar-json", type=Path, default=None)
    ap.add_argument("--rules-json", type=Path, default=DEFAULT_RULES)
    ap.add_argument("--eval-json", type=Path, default=DEFAULT_EVAL)
    ap.add_argument("--neutral-bundle-json", type=Path, default=DEFAULT_NEUTRAL)
    ap.add_argument("--myeongni-jsonl", type=Path, default=DEFAULT_MYEONGNI_JSONL)
    ap.add_argument("--sasang-jsonl", type=Path, default=DEFAULT_SASANG_JSONL)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    cal_path = _resolve_calendar_path(args.calendar_json, year_month=args.year_month)
    calendar = _read_json(cal_path)
    if not calendar.get("rows"):
        raise SystemExit(f"Missing calendar rows: {cal_path}")

    doc = build_audit(
        calendar=calendar,
        rules=_read_json(args.rules_json),
        eval_doc=_read_json(args.eval_json) if args.eval_json.is_file() else None,
        neutral_bundle=_read_json(args.neutral_bundle_json) if args.neutral_bundle_json.is_file() else None,
        myeongni_jsonl=args.myeongni_jsonl,
        sasang_jsonl=args.sasang_jsonl,
        calendar_path=cal_path,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    sc = doc["scored_day_counterfactuals"]
    print(
        f"WROTE: {args.output.resolve()} "
        f"neutral_anatomy={len(doc.get('neutral_vote_anatomy') or [])} "
        f"scored_active_soft={sc.get('active_soft_hit_rate')} "
        f"unlock_soft={sc.get('four_ai_unlock_soft_hit_rate')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
