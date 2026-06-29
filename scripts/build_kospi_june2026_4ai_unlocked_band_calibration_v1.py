#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""[HYPO] 4AI unlock shadow: neutral_bps × band-width sweep (direction vs band_hit) [research_only]."""

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

from scripts.eval_kospi_june2026_daily_prophecy_v1 import (  # noqa: E402
    KOSPI_CSV,
    _default_as_of_kst,
    _direction_from_return,
    _load_ohlcv_state,
    _outcome,
    _read_json,
)

DEFAULT_UNLOCK_CAL = ROOT / "reports/kospi_202606_4ai_unlock_shadow_calendar_v1.json"
DEFAULT_ACTIVE_CAL = ROOT / "docs/final/artifacts/kospi_202606_daily_prophecy_calendar_latest.json"
DEFAULT_OUT = ROOT / "reports/kospi_june2026_4ai_unlocked_band_calibration_v1_latest.json"
DEFAULT_ART = ROOT / "docs/final/artifacts/kospi_june2026_4ai_unlocked_band_calibration_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _metrics_from_scored(scored: list[dict[str, Any]]) -> dict[str, Any]:
    hits = sum(1 for s in scored if s["outcome"] == "HIT")
    fails = sum(1 for s in scored if s["outcome"] == "FAIL")
    neutral = sum(1 for s in scored if s["outcome"] == "NEUTRAL_DRAW")
    n_dir = hits + fails
    band_hits = sum(1 for s in scored if s.get("band_hit") is True)
    band_miss = sum(1 for s in scored if s.get("band_hit") is False)
    return {
        "n_scored": len(scored),
        "hit": hits,
        "fail": fails,
        "neutral_draw": neutral,
        "directional_hit_rate": round(hits / n_dir, 4) if n_dir else None,
        "soft_hit_rate": round((hits + 0.5 * neutral) / len(scored), 4) if scored else None,
        "band_hit_count": band_hits,
        "band_miss_count": band_miss,
        "band_hit_rate": round(band_hits / (band_hits + band_miss), 4)
        if (band_hits + band_miss)
        else None,
    }


def _score_calendar(
    calendar: dict[str, Any],
    *,
    as_of_kst: str,
    neutral_bps: float,
    band_scale: float,
    vol_band_k: float | None = None,
    vol_window: int = 5,
) -> list[dict[str, Any]]:
    from scripts.kospi_krx_calendar_v1 import exclude_krx_non_trading

    closes, vendor_incomplete_all = _load_ohlcv_state(KOSPI_CSV)
    raw_trading_days = list(calendar.get("trading_days") or [])
    trading_days, _ = exclude_krx_non_trading(raw_trading_days)
    row_by_date = {str(r.get("session_date")): r for r in calendar.get("rows") or [] if r.get("session_date")}

    # log returns for vol proxy
    log_rets: dict[str, float] = {}
    ordered = sorted(closes)
    for i, dk in enumerate(ordered):
        if i == 0:
            continue
        p0, p1 = closes[ordered[i - 1]], closes[dk]
        if p0 > 0 and p1 > 0:
            log_rets[dk] = __import__("math").log(p1 / p0)

    scored: list[dict[str, Any]] = []
    for dk in trading_days:
        if dk > as_of_kst:
            continue
        if dk in vendor_incomplete_all or dk not in closes:
            continue
        prow = row_by_date.get(dk)
        if not prow:
            continue
        older = sorted(d for d in closes if d < dk)
        prior = closes[older[-1]] if older else None
        if prior is None or prior <= 0:
            continue

        close = closes[dk]
        ret = (close - prior) / prior
        actual_dir = _direction_from_return(ret, neutral_bps)
        pred_dir = str(prow.get("predicted_direction") or "neutral")
        outcome = _outcome(pred_dir, actual_dir)

        band = prow.get("kospi_index_prophecy") if isinstance(prow.get("kospi_index_prophecy"), dict) else {}
        band_pct = band.get("predicted_return_band_pct") or [None, None]
        mid_pct = band.get("predicted_return_mid_pct")
        scale = float(band_scale)
        lo_pct = float(band_pct[0]) * scale if band_pct[0] is not None else None
        hi_pct = float(band_pct[1]) * scale if band_pct[1] is not None else None

        if vol_band_k is not None and vol_window > 1:
            window_dates = [d for d in older if d in log_rets][-vol_window:]
            if len(window_dates) >= 2:
                import statistics

                vol = statistics.pstdev([log_rets[d] for d in window_dates])
                vol_pct = vol * 100.0 * float(vol_band_k)
                if lo_pct is not None:
                    lo_pct = min(lo_pct, -abs(vol_pct))
                if hi_pct is not None:
                    hi_pct = max(hi_pct, abs(vol_pct))

        band_hit = None
        if lo_pct is not None and hi_pct is not None:
            lo_close = prior * (1.0 + lo_pct / 100.0)
            hi_close = prior * (1.0 + hi_pct / 100.0)
            band_hit = float(min(lo_close, hi_close)) <= close <= float(max(lo_close, hi_close))

        scored.append(
            {
                "session_date": dk,
                "predicted_direction": pred_dir,
                "actual_direction": actual_dir,
                "outcome": outcome,
                "daily_return_pct": round(ret * 100.0, 4),
                "band_hit": band_hit,
                "band_scale": scale,
                "neutral_bps": neutral_bps,
            }
        )
    return scored


def build_calibration(
    *,
    unlock_calendar_path: Path,
    active_calendar_path: Path,
    as_of_kst: str,
    neutral_bps_grid: list[float],
    band_scale_grid: list[float],
    vol_band_k_grid: list[float | None],
) -> dict[str, Any]:
    unlock_cal = _read_json(unlock_calendar_path)
    active_cal = _read_json(active_calendar_path)
    if not unlock_cal.get("rows"):
        raise SystemExit(f"unlock calendar empty: {unlock_calendar_path}")

    baseline_unlock = _metrics_from_scored(
        _score_calendar(unlock_cal, as_of_kst=as_of_kst, neutral_bps=5.0, band_scale=1.0)
    )
    baseline_active = _metrics_from_scored(
        _score_calendar(active_cal, as_of_kst=as_of_kst, neutral_bps=5.0, band_scale=1.0)
    ) if active_cal.get("rows") else None

    variants: list[dict[str, Any]] = []
    for nbps in neutral_bps_grid:
        for bscale in band_scale_grid:
            for vol_k in vol_band_k_grid:
                scored = _score_calendar(
                    unlock_cal,
                    as_of_kst=as_of_kst,
                    neutral_bps=float(nbps),
                    band_scale=float(bscale),
                    vol_band_k=vol_k,
                )
                m = _metrics_from_scored(scored)
                slug = f"nbps_{int(nbps)}_bscale_{bscale:.1f}"
                if vol_k is not None:
                    slug += f"_volk_{vol_k:.1f}"
                variants.append(
                    {
                        "variant_id": slug,
                        "neutral_bps": float(nbps),
                        "band_scale": float(bscale),
                        "vol_band_k": vol_k,
                        "metrics": m,
                        "delta_vs_unlock_baseline": {
                            "directional_hit_rate": round(
                                (m.get("directional_hit_rate") or 0)
                                - (baseline_unlock.get("directional_hit_rate") or 0),
                                4,
                            )
                            if m.get("directional_hit_rate") is not None
                            else None,
                            "soft_hit_rate": round(
                                (m.get("soft_hit_rate") or 0) - (baseline_unlock.get("soft_hit_rate") or 0),
                                4,
                            )
                            if m.get("soft_hit_rate") is not None
                            else None,
                            "band_hit_rate": round(
                                (m.get("band_hit_rate") or 0) - (baseline_unlock.get("band_hit_rate") or 0),
                                4,
                            )
                            if m.get("band_hit_rate") is not None
                            else None,
                        },
                    }
                )

    # Pareto-friendly picks: max band_hit_rate with directional HR >= baseline
    base_dir = baseline_unlock.get("directional_hit_rate") or 0.0
    eligible = [v for v in variants if (v["metrics"].get("directional_hit_rate") or 0) >= base_dir]
    best_band = max(eligible, key=lambda v: v["metrics"].get("band_hit_rate") or 0.0) if eligible else None
    best_joint = max(
        variants,
        key=lambda v: (
            (v["metrics"].get("band_hit_rate") or 0) * 0.5
            + (v["metrics"].get("soft_hit_rate") or 0) * 0.5
        ),
    )

    return {
        "schema": "kospi_june2026_4ai_unlocked_band_calibration_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "auto_apply": False,
        "apply_forbidden": True,
        "boundary_ack": "[HYPO] Shadow-only band/neutral_bps sweep on 4AI unlock calendar; not active apply.",
        "as_of_kst": as_of_kst,
        "unlock_calendar_path": _rel(unlock_calendar_path),
        "active_calendar_path": _rel(active_calendar_path),
        "baseline": {
            "unlock_shadow": baseline_unlock,
            "active_published": baseline_active,
        },
        "grid": {
            "neutral_bps": neutral_bps_grid,
            "band_scale": band_scale_grid,
            "vol_band_k": vol_band_k_grid,
        },
        "variants": variants,
        "recommended_shadow_only": {
            "best_band_hit_preserving_direction": best_band,
            "best_joint_soft_and_band": best_joint,
        },
        "verdict_ko": (
            f"unlock baseline dir={baseline_unlock.get('directional_hit_rate')} band={baseline_unlock.get('band_hit_rate')} "
            f"(n={baseline_unlock.get('n_scored')}). "
            "band_scale↑는 band_hit_rate 개선 가능하나 방향 HR 훼손 여부 병기. apply 금지."
        ),
        "reproduce": "py scripts/build_kospi_june2026_4ai_unlocked_band_calibration_v1.py",
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--unlock-calendar-json", type=Path, default=DEFAULT_UNLOCK_CAL)
    ap.add_argument("--active-calendar-json", type=Path, default=DEFAULT_ACTIVE_CAL)
    ap.add_argument("--as-of-kst", default=None)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--artifact", type=Path, default=DEFAULT_ART)
    args = ap.parse_args(argv)

    as_of = args.as_of_kst or _default_as_of_kst()
    doc = build_calibration(
        unlock_calendar_path=args.unlock_calendar_json.resolve(),
        active_calendar_path=args.active_calendar_json.resolve(),
        as_of_kst=as_of,
        neutral_bps_grid=[5.0, 10.0, 15.0, 20.0, 25.0],
        band_scale_grid=[1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0],
        vol_band_k_grid=[None, 2.0, 3.0],
    )
    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(payload, encoding="utf-8")
    args.artifact.parent.mkdir(parents=True, exist_ok=True)
    args.artifact.write_text(payload, encoding="utf-8")

    base = doc["baseline"]["unlock_shadow"]
    best = (doc.get("recommended_shadow_only") or {}).get("best_band_hit_preserving_direction") or {}
    bm = best.get("metrics") or {}
    print(
        f"WROTE: {args.output.resolve()} "
        f"n={base.get('n_scored')} baseline_band={base.get('band_hit_rate')} "
        f"best_band={bm.get('band_hit_rate')} variant={best.get('variant_id')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
