#!/usr/bin/env python3
"""[HYPO] RQ-031 — 연대기×역사 × KOSPI (research_only, NON_GATING).

Three pillars (NOT daily direction hit rate vs 63.2% majority):
  A) regime_map primary vs logos bridge / macro landmark tags (alignment rate)
  B) chronology_window vs KOSPI structural stats (vol, drawdown, transitions)
  C) general prophecy Brier + logos era-blind eval pointers (separate B-track axes)

Does not mutate ops score, Track A, or live trading gates.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, pstdev
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_OUT = ROOT / "reports/rq031_kospi_chronology_history_alignment_v1_latest.json"
DEFAULT_POINTER = ROOT / "reports/rq031_kospi_chronology_history_research_v1_latest.json"
SCHEMA = "rq031_kospi_chronology_history_alignment_v1"

DEFAULT_KOSPI = ROOT / "research/market_data/kospi_daily_external_yf.csv"
DEFAULT_REGIME_MAP = ROOT / "data/regimes/regime_map.json"
DEFAULT_QUAD = ROOT / "data/quad_fusion_training/quad_fusion_result_20260308_230751.json"
DEFAULT_CHRONOLOGY = ROOT / "docs/final/artifacts/logos_chronology_v1_latest.json"
DEFAULT_GOLD = ROOT / "docs/final/artifacts/fixtures/logos_chronology_historical_era_gold_v1.json"
DEFAULT_ERA_BLIND = ROOT / "reports/logos_chronology_era_blind_eval_v1_latest.json"
DEFAULT_BRIER = ROOT / "docs/final/artifacts/general_prophecy_brier_eval_latest.json"

# [HYPO] observational windows — aligned to logos_chronology modern_bridges window_id labels.
CHRONOLOGY_WINDOWS: dict[str, tuple[str, str, list[str]]] = {
    "imf_asian_crisis": ("1997-07-01", "1998-12-31", ["imf", "risk"]),
    "it_bubble_cycle": ("1999-01-01", "2002-12-31", ["it_bubble", "risk"]),
    "lehman_crisis": ("2008-09-01", "2009-06-30", ["lehman", "risk"]),
    "post_gfc_repair": ("2009-03-09", "2014-12-31", ["imf", "stability"]),
    "pandemic_shock": ("2020-02-01", "2020-06-30", ["covid", "risk"]),
    "rate_hike_cycle": ("2022-01-01", "2023-12-31", ["risk", "caution"]),
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def _quad_year_vectors(quad_json: Path) -> dict[int, dict[str, float]]:
    quad = _load_json(quad_json) or {}
    out: dict[int, dict[str, float]] = {}
    for row in quad.get("uft_v2_timeline") or []:
        yr = int(row.get("year", -1))
        u4 = row.get("unified_4d_vector") or {}
        if yr < 0 or not u4:
            continue
        out[yr] = {k: float(u4[k]) for k in ("S", "L", "K", "M") if k in u4}
    return out


def _primary_regime_for_year(
    year: int,
    *,
    year_vecs: dict[int, dict[str, float]],
    regime_map: Path,
) -> dict[str, Any]:
    u4 = year_vecs.get(year) or year_vecs.get(year - 1)
    if not u4:
        return {"year": year, "primary_regime_id": None, "top_cosine": None, "vector_source": "missing_quad"}
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from scripts.build_field_regime_per_date_attachment_hypo_v1 import _rank_primary  # noqa: WPS433

    ranked = _rank_primary(
        u4,
        regime_map=regime_map,
        exclude_regime_ids={"unknown"},
        vector_source=f"quad_year_flat_{year}",
    )
    return {"year": year, **ranked}


def _build_year_ohlcv_primary_cache(
    kospi_csv: Path,
    *,
    regime_map: Path,
) -> dict[int, dict[str, Any]]:
    """Year-end KOSPI OHLCV 4D proxy → regime_map primary ([HYPO], observation-only)."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from scripts.btrack_causal_ohlc_features_v1 import build_causal_feature_map, load_btc_ohlc_by_date  # noqa: WPS433
    from scripts.build_field_regime_per_date_attachment_hypo_v1 import _rank_primary  # noqa: WPS433

    ohlc = load_btc_ohlc_by_date(kospi_csv)
    feat_map = build_causal_feature_map(ohlc)
    closes = {d: bar["close"] for d, bar in ohlc.items()}
    cache: dict[int, dict[str, Any]] = {}
    for yr in sorted({int(d[:4]) for d in closes}):
        dates_y = sorted(d for d in closes if d.startswith(f"{yr}-"))
        if not dates_y:
            continue
        eval_date = dates_y[-1]
        feat = feat_map.get(eval_date)
        if not feat:
            continue
        vol5 = float(feat.get("realized_vol_5d") or 0.0)
        dd = abs(float(feat.get("drawdown_20d") or 0.0))
        pr = float(feat.get("prior_range_position") or 0.5)
        ovn = abs(float(feat.get("overnight_return") or 0.0))
        s = min(1.0, ovn * 8.0 + pr * 0.35)
        l = min(1.0, max(0.0, 1.0 - vol5 * 10.0))
        k = min(1.0, vol5 * 12.0)
        m = min(1.0, dd * 4.0)
        total = s + l + k + m
        if total <= 0:
            u4 = {"S": 0.25, "L": 0.25, "K": 0.25, "M": 0.25}
        else:
            u4 = {axis: val / total for axis, val in (("S", s), ("L", l), ("K", k), ("M", m))}
        ranked = _rank_primary(
            u4,
            regime_map=regime_map,
            exclude_regime_ids={"unknown"},
            vector_source=f"ohlcv_year_end_{yr}",
        )
        cache[yr] = {"year": yr, "eval_date": eval_date, **ranked}
    return cache


def _macro_landmarks(gold: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for ev in gold.get("events") or []:
        if not isinstance(ev, dict):
            continue
        if str(ev.get("tier") or "") != "macro_landmark":
            continue
        out.append(ev)
    return sorted(out, key=lambda e: str(e.get("as_of_date") or ""))


def _pillar_a_regime_alignment(
    *,
    gold: dict[str, Any],
    year_vecs: dict[int, dict[str, float]],
    regime_map: Path,
    kospi_csv: Path,
    year_ohlcv_cache: dict[int, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if year_ohlcv_cache is None:
        year_ohlcv_cache = _build_year_ohlcv_primary_cache(kospi_csv, regime_map=regime_map)
    events = _macro_landmarks(gold)
    rows: list[dict[str, Any]] = []
    strict_quad_hits = quad_covered = 0
    strict_ohlcv_hits = ohlcv_covered = 0
    n = 0
    quad_years = sorted(year_vecs)
    for ev in events:
        as_of = str(ev.get("as_of_date") or "")[:10]
        if len(as_of) < 4:
            continue
        yr = int(as_of[:4])
        primary = _primary_regime_for_year(yr, year_vecs=year_vecs, regime_map=regime_map)
        source = "quad_uft_v2"
        has_quad = yr in year_vecs or (yr - 1) in year_vecs
        if not primary.get("primary_regime_id"):
            ohlcv_row = year_ohlcv_cache.get(yr)
            if ohlcv_row and ohlcv_row.get("primary_regime_id"):
                primary = ohlcv_row
                source = "ohlcv_year_end_proxy"
        pid = primary.get("primary_regime_id")
        tags = [str(t).strip().lower() for t in (ev.get("inferred_regime_tags") or []) if str(t).strip()]
        gold_era = str(ev.get("gold_era_id") or "")
        strict = bool(pid and tags and pid in tags)
        if has_quad and primary.get("vector_source", "").startswith("quad"):
            quad_covered += 1
            if strict:
                strict_quad_hits += 1
        if source == "ohlcv_year_end_proxy" and pid:
            ohlcv_covered += 1
            if strict:
                strict_ohlcv_hits += 1
        n += 1
        rows.append(
            {
                "event_id": ev.get("event_id"),
                "as_of_date": as_of,
                "headline_ko": ev.get("headline_ko"),
                "inferred_regime_tags": tags,
                "primary_regime_id": pid,
                "primary_source": source,
                "top_cosine": primary.get("top_cosine"),
                "quad_year_available": has_quad,
                "strict_regime_tag_match": strict,
                "gold_era_id": gold_era,
            }
        )
    any_covered = quad_covered + ohlcv_covered
    any_strict = strict_quad_hits + strict_ohlcv_hits
    return {
        "n_macro_landmarks": n,
        "quad_timeline_year_min": quad_years[0] if quad_years else None,
        "quad_timeline_year_max": quad_years[-1] if quad_years else None,
        "quad_coverage_rate": round(quad_covered / n, 6) if n else None,
        "ohlcv_year_proxy_coverage_rate": round(ohlcv_covered / n, 6) if n else None,
        "combined_primary_coverage_rate": round(any_covered / n, 6) if n else None,
        "strict_primary_in_inferred_tags_rate_quad_only": round(strict_quad_hits / quad_covered, 6) if quad_covered else None,
        "strict_primary_in_inferred_tags_rate_ohlcv_proxy_only": round(strict_ohlcv_hits / ohlcv_covered, 6)
        if ohlcv_covered
        else None,
        "strict_primary_in_inferred_tags_rate_combined": round(any_strict / any_covered, 6) if any_covered else None,
        "strict_primary_in_inferred_tags_rate_all_events": round(any_strict / n, 6) if n else None,
        "interpretation_ko": (
            "[HYPO] macro landmark 연도 regime_map 1차: quad uft_v2 우선, 없으면 KOSPI OHLCV 연말 proxy. "
            "era 정렬은 Pillar C blind eval. 일봉 방향 hit 아님 · NON_GATING."
        ),
        "rows": rows,
    }


def _daily_returns(closes: dict[str, float]) -> dict[str, float]:
    out: dict[str, float] = {}
    for i, d in enumerate(sorted(closes)):
        if i == 0:
            continue
        prev = sorted(closes)[i - 1]
        c0, c1 = closes[prev], closes[d]
        if c0 == 0:
            continue
        out[d] = (c1 - c0) / c0
    return out


def _max_drawdown(closes: dict[str, float], dates: list[str]) -> float | None:
    if not dates:
        return None
    peak = closes[dates[0]]
    worst = 0.0
    for d in dates:
        c = closes.get(d)
        if c is None:
            continue
        peak = max(peak, c)
        if peak <= 0:
            continue
        dd = (c - peak) / peak
        worst = min(worst, dd)
    return round(worst, 6)


def _window_stats(
    closes: dict[str, float],
    rets: dict[str, float],
    start: str,
    end: str,
) -> dict[str, Any] | None:
    dates = sorted(d for d in closes if start <= d <= end)
    if len(dates) < 5:
        return None
    rvals = [rets[d] for d in dates if d in rets]
    if len(rvals) < 4:
        return None
    vol_ann = pstdev(rvals) * math.sqrt(252) if len(rvals) >= 2 else None
    return {
        "start": start,
        "end": end,
        "n_trading_days": len(dates),
        "mean_abs_daily_return": round(mean(abs(x) for x in rvals), 6),
        "realized_vol_ann": round(vol_ann, 6) if vol_ann is not None else None,
        "max_drawdown": _max_drawdown(closes, dates),
        "total_return": round((closes[dates[-1]] - closes[dates[0]]) / closes[dates[0]], 6)
        if closes.get(dates[0])
        else None,
    }


def _year_transition_count(
    dates: list[str],
    *,
    year_vecs: dict[int, dict[str, float]],
    regime_map: Path,
) -> int:
    years = sorted({int(d[:4]) for d in dates})
    primaries: list[str | None] = []
    for yr in years:
        primaries.append(_primary_regime_for_year(yr, year_vecs=year_vecs, regime_map=regime_map).get("primary_regime_id"))
    return sum(1 for i in range(1, len(primaries)) if primaries[i] != primaries[i - 1])


def _pillar_b_structural_windows(
    *,
    kospi_csv: Path,
    year_vecs: dict[int, dict[str, float]],
    regime_map: Path,
) -> dict[str, Any]:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from scripts.btrack_causal_ohlc_features_v1 import load_btc_ohlc_by_date  # noqa: WPS433

    ohlc = load_btc_ohlc_by_date(kospi_csv)
    closes = {d: bar["close"] for d, bar in ohlc.items()}
    rets = _daily_returns(closes)
    all_dates = sorted(closes)

    baseline = _window_stats(closes, rets, all_dates[0], all_dates[-1])
    windows_out: list[dict[str, Any]] = []
    for wid, (start, end, tags) in CHRONOLOGY_WINDOWS.items():
        stats = _window_stats(closes, rets, start, end)
        if not stats or not baseline:
            windows_out.append({"window_id": wid, "status": "insufficient_data", "expected_tags": tags})
            continue
        b_vol = baseline.get("realized_vol_ann") or 0.0
        w_vol = stats.get("realized_vol_ann") or 0.0
        vol_ratio = round(w_vol / b_vol, 4) if b_vol > 0 else None
        windows_out.append(
            {
                "window_id": wid,
                "expected_regime_tags": tags,
                "stats": stats,
                "vs_full_sample_baseline": {
                    "baseline_vol_ann": b_vol,
                    "window_vol_ratio": vol_ratio,
                    "baseline_max_dd": baseline.get("max_drawdown"),
                    "window_max_dd": stats.get("max_drawdown"),
                },
                "year_regime_transitions_in_window": _year_transition_count(
                    [d for d in all_dates if start <= d <= end],
                    year_vecs=year_vecs,
                    regime_map=regime_map,
                ),
            }
        )

    computable = [w for w in windows_out if w.get("stats")]
    insufficient = [w["window_id"] for w in windows_out if w.get("status") == "insufficient_data"]
    stress_windows = [w for w in computable if w.get("window_id") in ("lehman_crisis", "pandemic_shock", "imf_asian_crisis")]
    calm_windows = [w for w in computable if w.get("window_id") == "post_gfc_repair"]
    stress_vol = [
        w["vs_full_sample_baseline"]["window_vol_ratio"]
        for w in stress_windows
        if w.get("vs_full_sample_baseline", {}).get("window_vol_ratio") is not None
    ]
    calm_vol = [
        w["vs_full_sample_baseline"]["window_vol_ratio"]
        for w in calm_windows
        if w.get("vs_full_sample_baseline", {}).get("window_vol_ratio") is not None
    ]
    return {
        "kospi_csv": str(kospi_csv),
        "kospi_history_first_date": all_dates[0] if all_dates else None,
        "kospi_history_last_date": all_dates[-1] if all_dates else None,
        "windows_insufficient_data": insufficient,
        "full_sample_baseline": baseline,
        "chronology_windows": windows_out,
        "stress_vs_calm_vol_ratio_summary": {
            "n_windows_computed": len(computable),
            "mean_stress_window_vol_ratio": round(mean(stress_vol), 4) if stress_vol else None,
            "post_gfc_repair_vol_ratio": calm_vol[0] if calm_vol else None,
            "interpretation_ko": (
                "[HYPO] shock 윈도우 변동성이 전체 baseline 대비 높고 repair 윈도우는 상대적으로 낮은지 "
                "구조 지표만 비교. 방향 예측·Track A 승격 아님."
            ),
        },
    }


def _pillar_c_pointer_axes(*, era_blind: dict[str, Any] | None, brier: dict[str, Any] | None) -> dict[str, Any]:
    era_sum = (era_blind or {}).get("summary") or {}
    brier_metrics = (brier or {}).get("metrics") or {}
    return {
        "logos_era_blind_eval": {
            "path": "reports/logos_chronology_era_blind_eval_v1_latest.json",
            "hit_at_1_strict": era_sum.get("hit_at_1_strict"),
            "hit_at_1_relaxed": era_sum.get("hit_at_1_relaxed"),
            "locked_eval_hit_at_1_strict": era_sum.get("locked_eval_hit_at_1_strict"),
            "n_events": era_sum.get("n_events"),
            "axis": "historical_event → biblical_era alignment (NOT KOSPI daily direction)",
            "non_gating": True,
        },
        "general_prophecy_brier": {
            "path": "docs/final/artifacts/general_prophecy_brier_eval_latest.json",
            "mean_brier_score": brier_metrics.get("mean_brier_score"),
            "n_evaluated": brier_metrics.get("n_evaluated"),
            "pending_count": brier_metrics.get("pending_count"),
            "axis": "general prophecy calibration (NOT price OHLCV hit rate)",
        },
        "deliberate_separation_from_rq025_030b": (
            "RQ-025..030b measured KOSPI daily directional HR vs train-majority 63.2%. "
            "RQ-031 measures era/regime alignment and structural windows — no comparable single win/loss score."
        ),
    }


def _synthesis(pillar_a: dict[str, Any], pillar_b: dict[str, Any], pillar_c: dict[str, Any]) -> dict[str, Any]:
    quad_cov = pillar_a.get("quad_coverage_rate")
    combined_cov = pillar_a.get("combined_primary_coverage_rate")
    strict_combined = pillar_a.get("strict_primary_in_inferred_tags_rate_combined")
    strict_ohlcv = pillar_a.get("strict_primary_in_inferred_tags_rate_ohlcv_proxy_only")
    stress = (pillar_b.get("stress_vs_calm_vol_ratio_summary") or {}).get("mean_stress_window_vol_ratio")
    era_hit = (pillar_c.get("logos_era_blind_eval") or {}).get("hit_at_1_strict")
    era_locked = (pillar_c.get("logos_era_blind_eval") or {}).get("locked_eval_hit_at_1_strict")
    findings: list[str] = []
    if quad_cov is not None:
        findings.append(
            f"Pillar A: quad uft_v2 coverage = {quad_cov:.1%} "
            f"(years {pillar_a.get('quad_timeline_year_min')}–{pillar_a.get('quad_timeline_year_max')})."
        )
    if combined_cov is not None and combined_cov != quad_cov:
        findings.append(f"Pillar A: OHLCV year-end proxy raises primary coverage to {combined_cov:.1%}.")
    if strict_combined is not None:
        ohlcv_note = f", ohlcv-only {strict_ohlcv:.1%}" if strict_ohlcv is not None else ""
        findings.append(
            f"Pillar A: combined strict primary ∈ inferred tags = {strict_combined:.1%}{ohlcv_note}."
        )
    if stress is not None:
        findings.append(
            f"Pillar B: mean shock-window vol/baseline ratio = {stress:.2f} (structural, not direction HR)."
        )
    elif pillar_b.get("windows_insufficient_data"):
        findings.append(
            f"Pillar B: KOSPI CSV from {pillar_b.get('kospi_history_first_date')} — "
            f"{len(pillar_b.get('windows_insufficient_data') or [])} chronology windows insufficient; "
            "only in-range windows scored."
        )
    if era_hit is not None:
        findings.append(f"Pillar C: logos era blind hit@1 strict = {era_hit:.1%} (history→era, separate axis).")
    if era_locked is not None:
        findings.append(
            f"Pillar C: locked_eval hit@1 strict = {era_locked:.1%} — MS/대외 인용 시 locked만 (gold_tags upper bound 아님)."
        )
    return {
        "findings": findings,
        "auto_promote_ready": False,
        "track_a_mutated": False,
        "recommended_next": None,
        "readout_ko": [
            "연대기×역사 축은 RQ-025~030b 일봉 majority(63.2%)와 다른 설계로 측정됨.",
            "성경 2차·Logos는 [NON_GATING] 해설·정렬률; 실전 트리거·ops score 변경 없음.",
            "구조 윈도우(vol/DD)와 era blind eval은 상호 보조 관측 — Track A 승격 근거 아님.",
        ],
    }


def build_report(
    *,
    kospi_csv: Path,
    regime_map: Path,
    quad_json: Path,
    gold_json: Path,
    era_blind_json: Path,
    brier_json: Path,
    chronology_json: Path,
) -> dict[str, Any]:
    gold = _load_json(gold_json)
    if not gold:
        raise FileNotFoundError(gold_json)
    year_vecs = _quad_year_vectors(quad_json)
    if not year_vecs:
        raise FileNotFoundError(f"missing quad timeline: {quad_json}")
    if not kospi_csv.is_file():
        raise FileNotFoundError(kospi_csv)
    if not regime_map.is_file():
        raise FileNotFoundError(regime_map)

    pillar_a = _pillar_a_regime_alignment(
        gold=gold,
        year_vecs=year_vecs,
        regime_map=regime_map,
        kospi_csv=kospi_csv,
    )
    pillar_b = _pillar_b_structural_windows(kospi_csv=kospi_csv, year_vecs=year_vecs, regime_map=regime_map)
    pillar_c = _pillar_c_pointer_axes(
        era_blind=_load_json(era_blind_json),
        brier=_load_json(brier_json),
    )
    synthesis = _synthesis(pillar_a, pillar_b, pillar_c)

    return {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "hypothesis_tag": "[HYPO]",
        "boundary_ack": True,
        "research_only": True,
        "non_gating": True,
        "track_a_status": "blocked",
        "auto_promote_ready": False,
        "purpose_ko": "연대기×역사 × KOSPI — regime 정렬·구조 윈도우·B-track Brier/era eval (일봉 HR 아님)",
        "inputs": {
            "kospi_csv": str(kospi_csv),
            "regime_map": str(regime_map),
            "quad_json": str(quad_json),
            "chronology_json": str(chronology_json),
            "gold_json": str(gold_json),
            "era_blind_json": str(era_blind_json),
            "brier_json": str(brier_json),
        },
        "pillar_a_regime_tag_alignment": pillar_a,
        "pillar_b_kospi_structural_windows": pillar_b,
        "pillar_c_separate_btrack_axes": pillar_c,
        "synthesis": synthesis,
        "not_measured": [
            "kospi_daily_directional_hit_rate",
            "wf_train_majority_63.2_beat",
            "live_trading_trigger",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--kospi-csv", type=Path, default=DEFAULT_KOSPI)
    ap.add_argument("--regime-map", type=Path, default=DEFAULT_REGIME_MAP)
    ap.add_argument("--quad-json", type=Path, default=DEFAULT_QUAD)
    ap.add_argument("--chronology-json", type=Path, default=DEFAULT_CHRONOLOGY)
    ap.add_argument("--gold-json", type=Path, default=DEFAULT_GOLD)
    ap.add_argument("--era-blind-json", type=Path, default=DEFAULT_ERA_BLIND)
    ap.add_argument("--brier-json", type=Path, default=DEFAULT_BRIER)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--pointer-json", type=Path, default=DEFAULT_POINTER)
    args = ap.parse_args()

    try:
        report = build_report(
            kospi_csv=args.kospi_csv,
            regime_map=args.regime_map,
            quad_json=args.quad_json,
            gold_json=args.gold_json,
            era_blind_json=args.era_blind_json,
            brier_json=args.brier_json,
            chronology_json=args.chronology_json,
        )
    except FileNotFoundError as exc:
        print(f"MISSING: {exc}", file=sys.stderr)
        return 2

    out = args.out_json if args.out_json.is_absolute() else ROOT / args.out_json
    ptr = args.pointer_json if args.pointer_json.is_absolute() else ROOT / args.pointer_json
    out.parent.mkdir(parents=True, exist_ok=True)
    ptr.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    pointer = {
        "schema": "rq031_kospi_chronology_history_research_v1",
        "generated_at_utc": report["generated_at_utc"],
        "hypothesis_tag": "[HYPO]",
        "research_only": True,
        "artifact": str(out),
        "pillar_a_quad_coverage_rate": report["pillar_a_regime_tag_alignment"].get("quad_coverage_rate"),
        "pillar_a_combined_coverage_rate": report["pillar_a_regime_tag_alignment"].get(
            "combined_primary_coverage_rate"
        ),
        "pillar_a_strict_regime_tag_rate_combined": report["pillar_a_regime_tag_alignment"].get(
            "strict_primary_in_inferred_tags_rate_combined"
        ),
        "pillar_a_strict_ohlcv_proxy_only": report["pillar_a_regime_tag_alignment"].get(
            "strict_primary_in_inferred_tags_rate_ohlcv_proxy_only"
        ),
        "pillar_b_mean_stress_vol_ratio": (
            report["pillar_b_kospi_structural_windows"]
            .get("stress_vs_calm_vol_ratio_summary", {})
            .get("mean_stress_window_vol_ratio")
        ),
        "pillar_c_era_blind_hit_at_1_strict": (
            report["pillar_c_separate_btrack_axes"].get("logos_era_blind_eval", {}).get("hit_at_1_strict")
        ),
        "synthesis": report["synthesis"],
    }
    ptr.write_text(json.dumps(pointer, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out), "pointer": str(ptr)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
