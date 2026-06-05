#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build monthly KOSPI per-trading-day prophecy calendar [HYPO][research_only].

Default month: 2026-06. Use --year-month 2026-07 for July, etc.

Profiles:
  v1 — session myeongni + momentum + logos snapshot
  v2_multilens — + myeongni/sasang/macro independent + Field regime + KOSPI causal ensemble
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_myeongni_jsonl_from_manseryeok_session_v1 import (  # noqa: E402
    _mapping_from_score,
    _score_from_session_pillars,
)
from scripts.kospi_june2026_multilens_blend_v1 import (  # noqa: E402
    blend_v2_multilens,
    default_weights_v2,
    integration_maturity_rubric,
    load_ensemble_kospi_per_date,
    load_static_lenses,
)

EVOLUTION_RULES = ROOT / "data/commander/kospi_june2026_prophecy_evolution_v1.json"
KOSPI_CSV = ROOT / "research/market_data/kospi_daily_external_yf.csv"


def _parse_year_month(year_month: str) -> tuple[str, date, date]:
    ym = str(year_month).strip()
    parts = ym.split("-")
    if len(parts) != 2:
        raise ValueError(f"year-month must be YYYY-MM, got {year_month!r}")
    y, m = int(parts[0]), int(parts[1])
    start = date(y, m, 1)
    if m == 12:
        end = date(y, 12, 31)
    else:
        end = date(y, m + 1, 1) - timedelta(days=1)
    return f"{y:04d}-{m:02d}", start, end


def _paths_for_month(year_month: str) -> tuple[Path, Path]:
    tag = year_month.replace("-", "")
    out = ROOT / f"reports/kospi_{tag}_daily_prophecy_calendar_v1.json"
    art = ROOT / f"docs/final/artifacts/kospi_{tag}_daily_prophecy_calendar_latest.json"
    return out, art


def _panel_csv_for_month(year_month: str) -> Path:
    tag = year_month.replace("-", "")
    return ROOT / f"reports/btrack_session_myeongni_panel_{tag}_monthly_prophecy.csv"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _krx_weekdays(d0: date, d1: date) -> list[str]:
    from scripts.kospi_krx_calendar_v1 import krx_trading_days

    return krx_trading_days(d0, d1)


def _load_closes(csv_path: Path) -> dict[str, float]:
    if not csv_path.is_file():
        return {}
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


def _prior_close(closes: dict[str, float], session_date: str) -> float | None:
    prior_dates = sorted(d for d in closes if d < session_date)
    return closes[prior_dates[-1]] if prior_dates else None


def _trading_days_before(closes: dict[str, float], session_date: str, n: int) -> list[str]:
    dates = sorted(d for d in closes if d < session_date)
    return dates[-n:] if dates else []


def _direction_ko(direction: str) -> str:
    m = {"bull": "상승", "bear": "하락", "neutral": "횡보·관측", "sideways": "횡보·관측"}
    return m.get(direction, direction)


def _logos_direction() -> tuple[str, float]:
    art = ROOT / "docs/final/artifacts/logos_independent_lens_latest.json"
    doc = _read_json(art)
    scores = doc.get("scores") if isinstance(doc.get("scores"), dict) else {}
    try:
        ds = float(scores.get("direction_score") or 0.0)
    except (TypeError, ValueError):
        ds = 0.0
    if ds > 0.08:
        return "bull", ds
    if ds < -0.08:
        return "bear", ds
    return "neutral", ds


def _momentum_overlay(closes: dict[str, float], session_date: str) -> tuple[str, float]:
    """3-day avg return sign before session_date (causal, cross-month)."""
    hist = _trading_days_before(closes, session_date, 4)
    rets: list[float] = []
    for i in range(1, len(hist)):
        d0, d1 = hist[i - 1], hist[i]
        c0, c1 = closes.get(d0), closes.get(d1)
        if c1 is None or c0 is None or c0 == 0:
            continue
        rets.append((c1 - c0) / c0)
    rets = rets[-3:]
    if not rets:
        return "neutral", 0.0
    avg = sum(rets) / len(rets)
    if avg > 0.003:
        return "bull", avg
    if avg < -0.003:
        return "bear", avg
    return "neutral", avg


def _blend_direction(
    *,
    session_map: str,
    session_score: float,
    momentum_dir: str,
    logos_dir: str,
    weights: dict[str, float],
    neutral_band: float,
) -> tuple[str, float, str]:
    votes = {"bull": 0.0, "bear": 0.0, "neutral": 0.0}
    w_sess = float(weights.get("session_myeongni", 0.55))
    w_mom = float(weights.get("momentum_overlay", 0.25))
    w_log = float(weights.get("logos_non_gating", 0.2))

    sess_dir = "neutral" if session_map == "sideways" else session_map
    for label, w in ((sess_dir, w_sess), (momentum_dir, w_mom), (logos_dir, w_log)):
        votes[label] = votes.get(label, 0.0) + w

    winner = max(votes, key=lambda k: votes[k])
    if votes[winner] < 0.34:
        winner = "neutral"
    blended_score = (
        w_sess * session_score
        + w_mom * (0.12 if momentum_dir == "bull" else -0.12 if momentum_dir == "bear" else 0.0)
        + w_log * (0.08 if logos_dir == "bull" else -0.08 if logos_dir == "bear" else 0.0)
    )
    blended_score = max(-1.0, min(1.0, blended_score))
    if abs(blended_score) <= neutral_band * 0.5 and winner in ("bull", "bear"):
        if votes.get("neutral", 0) >= votes.get(winner, 0) * 0.85:
            winner = "neutral"
    return winner, round(blended_score, 6), f"blend({sess_dir},{momentum_dir},{logos_dir})"


def _index_band(prior: float | None, blended_score: float) -> dict[str, Any]:
    if prior is None or prior <= 0:
        return {
            "prior_close": None,
            "predicted_return_mid_pct": round(blended_score * 0.8, 3),
            "predicted_return_band_pct": [-1.2, 1.2],
            "predicted_close_mid": None,
            "predicted_close_band": [None, None],
        }
    mid_pct = blended_score * 0.8
    band_half = 1.2 + abs(blended_score) * 0.5
    low_pct, high_pct = mid_pct - band_half, mid_pct + band_half
    return {
        "prior_close": round(prior, 2),
        "predicted_return_mid_pct": round(mid_pct, 3),
        "predicted_return_band_pct": [round(low_pct, 3), round(high_pct, 3)],
        "predicted_close_mid": round(prior * (1 + mid_pct / 100.0), 2),
        "predicted_close_band": [
            round(prior * (1 + low_pct / 100.0), 2),
            round(prior * (1 + high_pct / 100.0), 2),
        ],
    }


def _run_panel(trading_days: list[str], panel_csv: Path) -> int:
    if not trading_days:
        return 2
    cmd = [
        sys.executable,
        "scripts/build_btrack_session_instant_myeongni_panel_v1.py",
        "--date-from",
        trading_days[0],
        "--date-to",
        trading_days[-1],
        "--out-csv",
        str(panel_csv),
    ]
    return int(subprocess.run(cmd, cwd=str(ROOT)).returncode)


def _resolve_weights_candidate(rules: dict[str, Any], candidate_id: str | None) -> dict[str, float] | None:
    if not candidate_id:
        return None
    candidates = rules.get("blend_weights_v2_candidates")
    if not isinstance(candidates, dict):
        return None
    entry = candidates.get(candidate_id)
    if not isinstance(entry, dict):
        return None
    weights = entry.get("weights")
    return dict(weights) if isinstance(weights, dict) else None


def _resolve_active_v2_weights(rules: dict[str, Any]) -> tuple[dict[str, float], str | None]:
    """Prefer last human apply stamp; fall back to blend_weights_v2 on disk."""
    policy = rules.get("weight_candidate_policy")
    active_cid = None
    if isinstance(policy, dict):
        active_cid = policy.get("active_candidate_id")
    last_apply = rules.get("last_candidate_apply_id")
    if last_apply:
        cand = _resolve_weights_candidate(rules, str(last_apply))
        if cand:
            return cand, str(last_apply)
    if active_cid:
        cand = _resolve_weights_candidate(rules, str(active_cid))
        if cand:
            return cand, str(active_cid)
    w = rules.get("blend_weights_v2")
    if isinstance(w, dict) and w:
        return dict(w), None
    return default_weights_v2(), None


def build_calendar(
    *,
    year_month: str = "2026-06",
    skip_panel: bool = False,
    seal_date: str | None = None,
    profile: str = "v2_multilens",
    weights_override: dict[str, float] | None = None,
    weights_candidate_id: str | None = None,
) -> dict[str, Any]:
    ym, month_start, month_end = _parse_year_month(year_month)
    rules = _read_json(EVOLUTION_RULES)
    profile = str(profile or rules.get("multilens_profile") or "v2_multilens").strip()
    candidate_id = weights_candidate_id
    if profile == "v2_multilens":
        if weights_override:
            weights = dict(weights_override)
        elif candidate_id:
            resolved = _resolve_weights_candidate(rules, candidate_id)
            weights = resolved if resolved else (rules.get("blend_weights_v2") or default_weights_v2())
        else:
            weights, auto_cid = _resolve_active_v2_weights(rules)
            if auto_cid and not candidate_id:
                candidate_id = auto_cid
    else:
        weights = rules.get("blend_weights") if isinstance(rules.get("blend_weights"), dict) else {}
    neutral_band = float(rules.get("neutral_band", 0.06))

    trading_days = _krx_weekdays(month_start, month_end)
    panel_csv = _panel_csv_for_month(ym)

    if not skip_panel:
        rc = _run_panel(trading_days, panel_csv)
        if rc != 0:
            raise RuntimeError(f"session panel build failed exit {rc}")

    panel_by_date: dict[str, dict[str, str]] = {}
    if panel_csv.is_file():
        with panel_csv.open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                dk = str(row.get("session_local_date", ""))[:10]
                if dk:
                    panel_by_date[dk] = row

    closes = _load_closes(KOSPI_CSV)
    logos_dir, logos_score = _logos_direction()
    static_lenses = load_static_lenses() if profile == "v2_multilens" else {}
    ensemble_by_date = (
        load_ensemble_kospi_per_date(trading_days) if profile == "v2_multilens" else {}
    )

    rows: list[dict[str, Any]] = []
    for dk in trading_days:
        prow = panel_by_date.get(dk, {})
        pillars = {
            "year": str(prow.get("year_pillar") or ""),
            "month": str(prow.get("month_pillar") or ""),
            "day": str(prow.get("day_pillar") or ""),
            "hour": str(prow.get("hour_pillar") or ""),
        }
        session_score = _score_from_session_pillars(pillars)
        session_map = _mapping_from_score(session_score, neutral_band)
        mom_dir, mom_val = _momentum_overlay(closes, dk)
        if profile == "v2_multilens":
            blend_policy = rules.get("blend_policy_v2") if isinstance(rules.get("blend_policy_v2"), dict) else {}
            pred_dir, blend_score, blend_detail = blend_v2_multilens(
                session_map=session_map,
                session_score=session_score,
                momentum_dir=mom_dir,
                static_lenses=static_lenses,
                ensemble_row=ensemble_by_date.get(dk),
                weights=weights,
                neutral_band=neutral_band,
                blend_policy=blend_policy,
            )
            blend_note = blend_detail
        else:
            pred_dir, blend_score, blend_note = _blend_direction(
                session_map=session_map,
                session_score=session_score,
                momentum_dir=mom_dir,
                logos_dir=logos_dir,
                weights=weights,
                neutral_band=neutral_band,
            )
            blend_note = {"note": blend_note, "profile": "v1"}
        prior = _prior_close(closes, dk)
        index_band = _index_band(prior, blend_score)
        status = "sealed"
        if seal_date and dk > seal_date:
            status = "pending"
        elif seal_date and dk == seal_date:
            status = "sealed_today"

        rows.append(
            {
                "session_date": dk,
                "weekday_ko": ["월", "화", "수", "목", "금"][date.fromisoformat(dk).weekday()],
                "status": status,
                "predicted_direction": pred_dir,
                "predicted_direction_ko": _direction_ko(pred_dir),
                "session_direction_score": round(session_score, 6),
                "session_mapping_target": session_map,
                "pillars_session": pillars,
                "blend": blend_note
                if profile == "v2_multilens"
                else {
                    "weights": weights,
                    "momentum_direction": mom_dir,
                    "momentum_avg_return": round(mom_val, 6),
                    "logos_direction": logos_dir,
                    "logos_direction_score": round(logos_score, 4),
                    "blended_score": blend_score,
                    "note": blend_note,
                },
                "kospi_index_prophecy": index_band,
                "hypothesis_tier": "B",
                "research_only": True,
                "non_gating": True,
            }
        )

    schema = (
        "kospi_monthly_daily_prophecy_calendar_v2"
        if profile == "v2_multilens"
        else "kospi_monthly_daily_prophecy_calendar_v1"
    )
    doc: dict[str, Any] = {
        "schema": schema,
        "generated_at_utc": _utc_now(),
        "year_month": ym,
        "multilens_profile": profile,
        "weights_candidate_id": candidate_id,
        "blend_weights_applied": dict(weights) if profile == "v2_multilens" else None,
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "research_only": True,
        "track_wall": "no_track_a_live_auto_merge",
        "disclaimer_ko": rules.get("disclaimer_ko")
        or "세션 명리 [HYPO]. 지수 레벨은 참고 밴드. Track A·실매매 비연동.",
        "evolution_rules_path": str(EVOLUTION_RULES.relative_to(ROOT)).replace("\\", "/"),
        "kospi_csv": str(KOSPI_CSV.relative_to(ROOT)).replace("\\", "/"),
        "panel_csv": str(panel_csv.relative_to(ROOT)).replace("\\", "/"),
        "n_trading_days": len(rows),
        "trading_days": trading_days,
        "rows": rows,
        "daily_scoring_hook": "scripts/eval_kospi_june2026_daily_prophecy_v1.py",
        "evolution_hook": "scripts/run_kospi_june2026_prophecy_evolution_v1.py",
    }
    if profile == "v2_multilens":
        doc["static_lenses_snapshot"] = static_lenses
        doc["ensemble_kospi_causal_dates"] = sorted(ensemble_by_date.keys())
        doc["integration_maturity"] = integration_maturity_rubric(
            static_lenses, len(ensemble_by_date), len(trading_days)
        )
    return doc


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--year-month", type=str, default="2026-06", help="Calendar month YYYY-MM")
    ap.add_argument("--output", type=Path, default=None, help="Override report JSON path")
    ap.add_argument("--skip-panel-rebuild", action="store_true")
    ap.add_argument("--seal-date", type=str, default=None, help="YYYY-MM-DD marks sealed_today")
    ap.add_argument(
        "--profile",
        choices=("v1", "v2_multilens"),
        default="v2_multilens",
        help="Blend profile (default v2_multilens)",
    )
    ap.add_argument(
        "--weights-candidate-id",
        type=str,
        default=None,
        help="Use blend_weights_v2_candidates.<id> from evolution rules (shadow build)",
    )
    args = ap.parse_args(argv)

    report_out, art_out = _paths_for_month(args.year_month)
    if args.output is not None:
        report_out = args.output
    legacy_june = (
        ROOT / "reports/kospi_june2026_daily_prophecy_calendar_v1.json"
        if str(args.year_month).strip() == "2026-06"
        else None
    )

    doc = build_calendar(
        skip_panel=args.skip_panel_rebuild,
        seal_date=args.seal_date,
        profile=args.profile,
        year_month=args.year_month,
        weights_candidate_id=args.weights_candidate_id,
    )
    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    report_out.parent.mkdir(parents=True, exist_ok=True)
    report_out.write_text(payload, encoding="utf-8")
    art_out.parent.mkdir(parents=True, exist_ok=True)
    art_out.write_text(payload, encoding="utf-8")
    if legacy_june is not None:
        legacy_june.write_text(payload, encoding="utf-8")
    print(f"WROTE: {report_out.resolve()} rows={doc['n_trading_days']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
