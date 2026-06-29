#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Three-lens horizon empirical eval v2 [HYPO][research_only].

Extends v1 with:
  1) Per-date Logos/macro gate signals (causal macro_risk log + trailing OHLCV regime)
  2) Sasang intensity/stress vs realized short-horizon volatility
  3) Myeongni mid-horizon grid (5/10/15/20/21d) — contract mid_10d rank
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.run_three_lens_horizon_empirical_eval_v1 as v1  # noqa: E402
from scripts.btrack_multilens_per_date_core_v1 import (  # noqa: E402
    DEFAULT_LOGOS_LENS,
    DEFAULT_MYEONGNI_JSONL,
    DEFAULT_SASANG_JSONL,
    causal_rows_through,
    logos_global,
    read_jsonl,
    row_asof,
    rows_by_calendar_day,
    score_myeongni_at_date,
    sign_to_dir,
)
KOSPI_CSV = v1.KOSPI_CSV
BTC_CSV = v1.BTC_CSV
MACRO_LENS = v1.MACRO_LENS
DEFAULT_OUT = ROOT / "reports/three_lens_horizon_empirical_eval_v2_latest.json"
ART_OUT = ROOT / "docs/final/artifacts/three_lens_horizon_empirical_eval_v2_latest.json"
LOGOS_PER_DATE_JSONL = ROOT / "reports/three_lens_logos_per_date_macro_gate_v1.jsonl"

MACRO_RISK_LOG = ROOT / "reports/macro_risk/forward/macro_risk_forward_log_v1.jsonl"
MACRO_RISK_BACKFILL_LOG = ROOT / "reports/macro_risk/forward/macro_risk_forward_log_research_backfill_v1.jsonl"
FRAGILITY_LOG = ROOT / "reports/fragility_macro_risk_daily_run_log.jsonl"

MYEONGNI_GRID: dict[str, int] = {
    "mid_5d": 5,
    "mid_10d": 10,
    "mid_15d": 15,
    "mid_20d": 20,
    "macro_21d": 21,
}

LOGOS_VARIANTS = (
    "logos_global_snapshot",
    "logos_macro_risk_causal",
    "logos_trailing_regime_21d",
    "logos_macro_63d_trailing",
)

INTENSITY_RANK_MIN = 0.20
INTENSITY_ALERT_PREC_MIN = 0.25
INTENSITY_ALERT_REC_MIN = 0.20
INTENSITY_LEGACY_PREC_MIN = 0.45
INTENSITY_PERCENTILE_SWEEP = (70.0, 75.0, 80.0, 85.0)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(o, dict):
            rows.append(o)
    return rows


def _row_day(row: dict[str, Any]) -> str | None:
    for key in (
        "session_date",
        "eval_date",
        "calendar_date",
        "logged_at_utc",
        "ts_utc",
        "generated_at_utc",
        "source_snapshot_ts_utc",
    ):
        ts = str(row.get(key) or "")
        if len(ts) >= 10 and ts[4] == "-":
            return ts[:10]
    return None


def _decision_to_direction(decision_state: str | None, risk_level: str | None = None) -> str:
    s = str(decision_state or "").strip().upper()
    lvl = str(risk_level or "").strip().lower()
    if s in {"GO", "RISK_ON"}:
        return "bull"
    if s in {"REDUCE", "NO_GO", "HOLD", "LOCKED"}:
        return "bear"
    if s in {"CALM", "NEUTRAL", "NEUTRAL_BAND"}:
        return "neutral"
    if s == "WATCH" or lvl in {"elevated", "high", "critical"}:
        return "bear"
    return "neutral"


def _gate_row_ts(row: dict[str, Any]) -> str:
    return str(
        row.get("logged_at_utc")
        or row.get("ts_utc")
        or row.get("generated_at_utc")
        or row.get("source_snapshot_ts_utc")
        or ""
    )


def _signal_source_from_gate_row(row: dict[str, Any]) -> str:
    schema = str(row.get("schema") or "")
    if "research_backfill" in schema:
        return "research_backfill"
    if schema == "macro_risk_forward_log_row_v1":
        return "operational_causal"
    return "operational_causal"


def _build_gate_by_day_tiered(sources: list[tuple[int, Path]]) -> dict[str, dict[str, Any]]:
    """Higher priority wins per calendar day; same tier uses latest timestamp."""
    by_day: dict[str, tuple[int, dict[str, Any]]] = {}
    for priority, path in sources:
        if not path.is_file():
            continue
        for row in _read_jsonl(path):
            dk = _row_day(row)
            if not dk:
                continue
            prev = by_day.get(dk)
            if prev is None:
                by_day[dk] = (priority, row)
                continue
            prev_pri, prev_row = prev
            if priority > prev_pri:
                by_day[dk] = (priority, row)
            elif priority == prev_pri and _gate_row_ts(row) >= _gate_row_ts(prev_row):
                by_day[dk] = (priority, row)
    return {k: v[1] for k, v in by_day.items()}


def _gate_asof(by_day: dict[str, dict[str, Any]], eval_date: str) -> dict[str, Any] | None:
    eligible = [d for d in by_day if d <= eval_date[:10]]
    if not eligible:
        return None
    return by_day[max(eligible)]


def _trailing_return_sign(
    closes: dict[str, float],
    trading_days: list[str],
    idx: int,
    window: int,
    neutral_bps: float,
) -> str | None:
    if idx < window:
        return None
    d0 = trading_days[idx]
    d_back = trading_days[idx - window]
    c0 = closes.get(d0)
    c_back = closes.get(d_back)
    if c0 is None or c_back is None or c_back == 0:
        return None
    ret = (c0 - c_back) / c_back
    return v1._direction_from_return(ret, neutral_bps)


def _build_logos_per_date_rows(
    trading_days: list[str],
    closes: dict[str, float],
    *,
    neutral_bps: float,
    logos_lens: Path,
    gate_paths: list[tuple[int, Path]],
) -> list[dict[str, Any]]:
    logos_block = logos_global(logos_lens)
    global_dir = sign_to_dir(int(logos_block.get("sign") or 0))
    gate_by_day = _build_gate_by_day_tiered(gate_paths)
    out: list[dict[str, Any]] = []
    first_gate_day = min(gate_by_day.keys()) if gate_by_day else None
    for i, dk in enumerate(trading_days):
        gate_row = _gate_asof(gate_by_day, dk)
        trailing_dir = _trailing_return_sign(closes, trading_days, i, 21, neutral_bps)
        trailing_63_dir = _trailing_return_sign(closes, trading_days, i, 63, neutral_bps)
        if gate_row:
            macro_risk_dir = _decision_to_direction(
                str(gate_row.get("decision_state") or ""),
                str(gate_row.get("risk_warning_level") or ""),
            )
            macro_signal_source = _signal_source_from_gate_row(gate_row)
            macro_risk_mode = (
                "research_backfill_ohlcv_v1"
                if macro_signal_source == "research_backfill"
                else "causal_asof_macro_risk_log"
            )
            macro_risk_source = str(gate_row.get("schema") or "macro_gate_log")
        elif trailing_dir:
            macro_risk_dir = trailing_dir
            macro_risk_mode = "trailing_21d_fallback_no_causal_gate"
            macro_risk_source = None
            macro_signal_source = "trailing_fallback"
        else:
            macro_risk_dir = "neutral"
            macro_risk_mode = "no_signal"
            macro_risk_source = None
            macro_signal_source = "none"
        out.append(
            {
                "schema": "three_lens_logos_per_date_macro_gate_v1",
                "session_date": dk,
                "hypothesis_tier": "B",
                "research_only": True,
                "variants": {
                    "logos_global_snapshot": {
                        "direction": global_dir,
                        "mode": "global_snapshot_non_gating",
                    },
                    "logos_macro_risk_causal": {
                        "direction": macro_risk_dir,
                        "mode": macro_risk_mode,
                        "gate_source": macro_risk_source,
                        "signal_source": macro_signal_source,
                        "first_causal_gate_day": first_gate_day,
                    },
                    "logos_trailing_regime_21d": {
                        "direction": trailing_dir or "neutral",
                        "mode": "ohlcv_trailing_21d_regime_proxy",
                        "note": "Price-derived macro regime benchmark, not Logos RAG output.",
                    },
                    "logos_macro_63d_trailing": {
                        "direction": trailing_63_dir or "neutral",
                        "mode": "ohlcv_trailing_63d_macro_proxy",
                        "note": "Longer trailing window for macro_21d role hypothesis [HYPO].",
                    },
                },
            }
        )
    return out


def _write_logos_per_date_jsonl(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _eval_logos_variants(
    *,
    trading_days: list[str],
    labels: dict[str, dict[str, str]],
    logos_rows_by_date: dict[str, dict[str, Any]],
    min_n: int,
    min_soft_delta: float,
    macro_risk_coverage: dict[str, Any] | None = None,
) -> dict[str, Any]:
    scored: list[dict[str, Any]] = []
    eval_dates = [d for d in trading_days if d in labels and all(h in labels[d] for h in v1.HORIZONS)]
    for dk in eval_dates:
        lrow = logos_rows_by_date.get(dk) or {}
        variants = lrow.get("variants") if isinstance(lrow.get("variants"), dict) else {}
        for variant_id in LOGOS_VARIANTS:
            block = variants.get(variant_id) if isinstance(variants.get(variant_id), dict) else {}
            pred = str(block.get("direction") or "neutral")
            for hname in v1.HORIZONS:
                scored.append(
                    {
                        "lens_id": variant_id,
                        "horizon": hname,
                        "predicted_direction": pred,
                        "actual_direction": labels[dk][hname],
                        "outcome": v1._outcome(pred, labels[dk][hname]),
                        "role_matched_horizon": "macro_21d",
                        "horizon_is_role_match": hname == "macro_21d",
                    }
                )

    matrix = v1._rate_matrix(scored) if scored else {}
    # Rebuild matrix manually for variant ids only
    matrix = {}
    for variant_id in LOGOS_VARIANTS:
        matrix[variant_id] = {}
        for hname in v1.HORIZONS:
            rows = [r for r in scored if r.get("lens_id") == variant_id and r.get("horizon") == hname]
            hits = sum(1 for r in rows if r.get("outcome") == "HIT")
            fails = sum(1 for r in rows if r.get("outcome") == "FAIL")
            neutral = sum(1 for r in rows if r.get("outcome") == "NEUTRAL_DRAW")
            n = len(rows)
            n_dir = hits + fails
            matrix[variant_id][hname] = {
                "n_scored": n,
                "directional_hit_rate": round(hits / n_dir, 4) if n_dir else None,
                "soft_hit_rate": round((hits + 0.5 * neutral) / n, 4) if n else None,
            }

    role_map = {vid: "macro_21d" for vid in LOGOS_VARIANTS}
    cov = macro_risk_coverage or {}
    research_proxy_dominated = (
        float(cov.get("research_backfill_rate") or 0) >= 0.8
        and float(cov.get("operational_causal_rate") or 0) == 0
    )
    per_variant: dict[str, Any] = {}
    passes = 0
    effective_passes = 0
    for variant_id in LOGOS_VARIANTS:
        matched = matrix.get(variant_id, {}).get("macro_21d") or {}
        matched_soft = matched.get("soft_hit_rate")
        matched_n = int(matched.get("n_scored") or 0)
        best_h = None
        best_soft = None
        for hname in v1.HORIZONS:
            if hname == "macro_21d":
                continue
            val = (matrix.get(variant_id, {}).get(hname) or {}).get("soft_hit_rate")
            if val is None:
                continue
            if best_soft is None or float(val) > float(best_soft):
                best_soft = float(val)
                best_h = hname
        delta = None
        ok = False
        if matched_soft is not None and best_soft is not None and matched_n >= min_n:
            delta = round(float(matched_soft) - best_soft, 4)
            ok = delta >= min_soft_delta
            if ok:
                passes += 1
        proxy_only = (
            research_proxy_dominated
            and variant_id == "logos_macro_risk_causal"
            and ok
        )
        effective_ok = ok and not proxy_only
        if effective_ok:
            effective_passes += 1
        per_variant[variant_id] = {
            "matched_horizon": "macro_21d",
            "matched_soft_hit_rate": matched_soft,
            "best_mismatch_horizon": best_h,
            "best_mismatch_soft_hit_rate": best_soft,
            "soft_delta_matched_minus_best_mismatch": delta,
            "macro_alignment_pass": ok,
            "research_proxy_only": proxy_only,
            "macro_alignment_pass_effective": effective_ok,
        }

    return {
        "n_eval_dates": len(eval_dates),
        "variants": list(LOGOS_VARIANTS),
        "rate_matrix": matrix,
        "per_variant": per_variant,
        "variants_macro_alignment_pass": passes,
        "variants_macro_alignment_pass_effective": effective_passes,
        "best_variant_by_macro_soft": max(
            LOGOS_VARIANTS,
            key=lambda vid: float((matrix.get(vid, {}).get("macro_21d") or {}).get("soft_hit_rate") or -1.0),
        ),
        "macro_risk_coverage": macro_risk_coverage or _macro_risk_coverage(logos_rows_by_date),
        "note_ko": (
            "macro_risk: 인과 게이트 없으면 trailing_21d 폴백(중립 50% 편향 방지). "
            "trailing_regime_21d는 동일 OHLCV 벤치마크 별도 변종."
        ),
        "research_backfill_caveat_ko": (
            "research_backfill_rate≥0.8 이고 operational_causal=0이면 macro 정렬은 "
            "OHLCV 연구 프록시 근거 — Track C 운영 로그 실증 아님."
            if (macro_risk_coverage or {}).get("research_backfill_rate", 0) >= 0.8
            and (macro_risk_coverage or {}).get("operational_causal_rate", 0) == 0
            else None
        ),
    }


def _macro_risk_coverage(logos_rows_by_date: dict[str, dict[str, Any]]) -> dict[str, Any]:
    counts = {
        "operational_causal": 0,
        "research_backfill": 0,
        "trailing_fallback": 0,
        "none": 0,
    }
    first_gate: str | None = None
    for row in logos_rows_by_date.values():
        variants = row.get("variants") if isinstance(row.get("variants"), dict) else {}
        block = variants.get("logos_macro_risk_causal") if isinstance(variants.get("logos_macro_risk_causal"), dict) else {}
        src = str(block.get("signal_source") or "none")
        if src in counts:
            counts[src] += 1
        fg = block.get("first_causal_gate_day")
        if fg and first_gate is None:
            first_gate = str(fg)
    total = sum(counts.values()) or 1
    causal_n = counts["operational_causal"] + counts["research_backfill"]
    return {
        "n_dates": total,
        "by_signal_source": counts,
        "causal_coverage_rate": round(causal_n / total, 4),
        "operational_causal_rate": round(counts["operational_causal"] / total, 4),
        "research_backfill_rate": round(counts["research_backfill"] / total, 4),
        "first_causal_gate_day": first_gate,
    }


def _sasang_stress_score(row: dict[str, Any] | None) -> float:
    if not row:
        return 0.5
    mr = row.get("machine_readables") if isinstance(row.get("machine_readables"), dict) else {}
    try:
        heat = float(mr.get("heat_proxy") or 0.5)
        cold = float(mr.get("cold_proxy") or 0.5)
        vol = float(mr.get("volatility_rarefaction_proxy") or 0.5)
    except (TypeError, ValueError):
        return 0.5
    imbalance = abs(heat - cold)
    return max(0.0, min(1.0, 0.45 * vol + 0.35 * imbalance + 0.20 * max(heat, cold)))


def _sasang_stress_score_decoupled(row: dict[str, Any] | None) -> float:
    """Psych-only stress (heat/cold imbalance) — excludes vol proxy to reduce OHLCV label leakage."""
    if not row:
        return 0.5
    mr = row.get("machine_readables") if isinstance(row.get("machine_readables"), dict) else {}
    try:
        heat = float(mr.get("heat_proxy") or 0.5)
        cold = float(mr.get("cold_proxy") or 0.5)
    except (TypeError, ValueError):
        return 0.5
    imbalance = abs(heat - cold)
    return max(0.0, min(1.0, 0.55 * imbalance + 0.45 * max(heat, cold)))


def _realized_short_intensity(
    closes: dict[str, float],
    trading_days: list[str],
    idx: int,
    *,
    horizon_days: int = 5,
) -> float | None:
    if idx + horizon_days >= len(trading_days):
        return None
    rets: list[float] = []
    for j in range(1, horizon_days + 1):
        d0 = trading_days[idx + j - 1]
        d1 = trading_days[idx + j]
        c0 = closes.get(d0)
        c1 = closes.get(d1)
        if c0 is None or c1 is None or c0 == 0:
            return None
        rets.append(abs((c1 - c0) / c0))
    if not rets:
        return None
    return sum(rets) / len(rets)


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    xs = sorted(values)
    if len(xs) == 1:
        return xs[0]
    k = (len(xs) - 1) * (pct / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return xs[int(k)]
    return xs[f] * (c - k) + xs[c] * (k - f)


def _spearman_lite(pairs: list[dict[str, Any]]) -> float | None:
    n = len(pairs)
    if n <= 1:
        return None
    pred_rank = {id(p): i for i, p in enumerate(sorted(pairs, key=lambda x: x["pred_stress"]))}
    real_rank = {id(p): i for i, p in enumerate(sorted(pairs, key=lambda x: x["realized_intensity"]))}
    mean_d2 = sum((pred_rank[id(p)] - real_rank[id(p)]) ** 2 for p in pairs) / n
    return 1.0 - (6.0 * mean_d2) / (n * (n * n - 1))


def _alert_metrics_at_pct(pairs: list[dict[str, Any]], high_pct: float) -> dict[str, Any]:
    pred_scores = [p["pred_stress"] for p in pairs]
    real_scores = [p["realized_intensity"] for p in pairs]
    p_pred = _percentile(pred_scores, high_pct)
    p_real = _percentile(real_scores, high_pct)
    pred_high = [p for p in pairs if p["pred_stress"] >= p_pred]
    real_high = [p for p in pairs if p["realized_intensity"] >= p_real]
    both = [p for p in pairs if p["pred_stress"] >= p_pred and p["realized_intensity"] >= p_real]
    prec = len(both) / len(pred_high) if pred_high else None
    rec = len(both) / len(real_high) if real_high else None
    return {
        "high_percentile": high_pct,
        "pred_stress_p": round(p_pred, 6),
        "realized_intensity_p": round(p_real, 6),
        "high_stress_precision": round(prec, 4) if prec is not None else None,
        "high_stress_recall": round(rec, 4) if rec is not None else None,
        "alert_pass": (
            prec is not None
            and rec is not None
            and prec >= INTENSITY_ALERT_PREC_MIN
            and rec >= INTENSITY_ALERT_REC_MIN
        ),
    }


def _intensity_eval_from_pairs(
    pairs: list[dict[str, Any]],
    *,
    intensity_horizon_days: int,
    high_pct: float,
) -> dict[str, Any]:
    if len(pairs) < 10:
        return {"n_pairs": len(pairs), "status": "insufficient_data"}

    rank_corr = _spearman_lite(pairs)
    default_alert = _alert_metrics_at_pct(pairs, high_pct)
    sweep = [_alert_metrics_at_pct(pairs, pct) for pct in INTENSITY_PERCENTILE_SWEEP]
    best_alert = max(
        sweep,
        key=lambda row: (
            float(row.get("high_stress_precision") or -1.0) + float(row.get("high_stress_recall") or -1.0)
        ),
    )
    intensity_rank_pass = rank_corr is not None and rank_corr >= INTENSITY_RANK_MIN
    intensity_alert_pass = bool(best_alert.get("alert_pass"))
    intensity_pass_legacy = (
        rank_corr is not None
        and rank_corr >= 0.15
        and default_alert.get("high_stress_precision") is not None
        and float(default_alert["high_stress_precision"]) >= INTENSITY_LEGACY_PREC_MIN
    )
    spearman = round(rank_corr, 4) if rank_corr is not None else None
    return {
        "n_pairs": len(pairs),
        "intensity_horizon_days": intensity_horizon_days,
        "high_percentile_default": high_pct,
        "pred_stress_p": default_alert.get("pred_stress_p"),
        "realized_intensity_p": default_alert.get("realized_intensity_p"),
        "high_stress_precision": default_alert.get("high_stress_precision"),
        "high_stress_recall": default_alert.get("high_stress_recall"),
        "spearman_rank_corr": spearman,
        "percentile_sweep": sweep,
        "best_alert_sweep": best_alert,
        "intensity_rank_pass": intensity_rank_pass,
        "intensity_alert_pass": intensity_alert_pass,
        "intensity_pass_legacy": intensity_pass_legacy,
        "intensity_pass": intensity_rank_pass,
        "mechanical_proxy_suspect": spearman is not None and spearman > 0.99,
    }


def _eval_sasang_intensity(
    *,
    trading_days: list[str],
    closes: dict[str, float],
    sasang_by_day: dict[str, dict[str, Any]],
    intensity_horizon_days: int,
    high_pct: float,
) -> dict[str, Any]:
    pairs_legacy: list[dict[str, Any]] = []
    pairs_decoupled: list[dict[str, Any]] = []
    for i, dk in enumerate(trading_days):
        _, sa_asof = row_asof(sasang_by_day, dk)
        realized = _realized_short_intensity(closes, trading_days, i, horizon_days=intensity_horizon_days)
        if realized is None:
            continue
        base = {"session_date": dk, "realized_intensity": realized}
        pairs_legacy.append({**base, "pred_stress": _sasang_stress_score(sa_asof)})
        pairs_decoupled.append({**base, "pred_stress": _sasang_stress_score_decoupled(sa_asof)})

    legacy = _intensity_eval_from_pairs(
        pairs_legacy,
        intensity_horizon_days=intensity_horizon_days,
        high_pct=high_pct,
    )
    decoupled = _intensity_eval_from_pairs(
        pairs_decoupled,
        intensity_horizon_days=intensity_horizon_days,
        high_pct=high_pct,
    )

    gate_policy = {
        "rank_min": INTENSITY_RANK_MIN,
        "alert_prec_min": INTENSITY_ALERT_PREC_MIN,
        "alert_rec_min": INTENSITY_ALERT_REC_MIN,
        "legacy_prec_min": INTENSITY_LEGACY_PREC_MIN,
        "percentile_sweep": list(INTENSITY_PERCENTILE_SWEEP),
    }
    out = {**legacy, "gate_policy": gate_policy, "pred_mode": "legacy_vol_mix"}
    out["variants"] = {
        "legacy_vol_mix": {**legacy, "pred_mode": "legacy_vol_mix"},
        "decoupled_psych_only": {**decoupled, "pred_mode": "decoupled_psych_only"},
    }
    out["note_ko"] = (
        "사상 강도=machine_readables 스트레스 순위; 라벨=선행 단기 실현 변동성. "
        "legacy_vol_mix는 vol_proxy 포함(기계적 상관 의심); decoupled_psych_only는 heat/cold만. "
        "intensity_pass=순위상관(주); promotion은 decoupled variant 우선."
    )
    return out


def _build_grid_labels(
    trading_days: list[str],
    closes: dict[str, float],
    *,
    neutral_bps: float,
    horizons: dict[str, int],
) -> dict[str, dict[str, str]]:
    labels: dict[str, dict[str, str]] = {}
    for i, dk in enumerate(trading_days):
        row: dict[str, str] = {}
        for hname, hdays in horizons.items():
            fr = v1._forward_return(closes, trading_days, i, hdays)
            if fr is None:
                continue
            row[hname] = v1._direction_from_return(fr, neutral_bps)
        if row:
            labels[dk] = row
    return labels


def _eval_myeongni_grid(
    *,
    trading_days: list[str],
    grid_labels: dict[str, dict[str, str]],
    myeongni_by_day: dict[str, dict[str, Any]],
    myeongni_momentum_window: int,
    contract_horizon: str = "mid_10d",
) -> dict[str, Any]:
    eval_dates = [
        d
        for d in trading_days
        if d in grid_labels and all(h in grid_labels[d] for h in MYEONGNI_GRID)
    ]
    scored: list[dict[str, Any]] = []
    for dk in eval_dates:
        my_day, _ = row_asof(myeongni_by_day, dk)
        my_hist = causal_rows_through(myeongni_by_day, dk)
        my = score_myeongni_at_date(
            my_hist,
            eval_date=dk,
            matched_day=my_day,
            momentum_window=myeongni_momentum_window,
        )
        pred = v1._score_to_direction(float(my.get("direction_score") or 0.0))
        for hname in MYEONGNI_GRID:
            actual = grid_labels[dk][hname]
            scored.append(
                {
                    "horizon": hname,
                    "predicted_direction": pred,
                    "actual_direction": actual,
                    "outcome": v1._outcome(pred, actual),
                }
            )

    matrix: dict[str, dict[str, float | int | None]] = {}
    for hname in MYEONGNI_GRID:
        rows = [r for r in scored if r.get("horizon") == hname]
        hits = sum(1 for r in rows if r.get("outcome") == "HIT")
        fails = sum(1 for r in rows if r.get("outcome") == "FAIL")
        neutral = sum(1 for r in rows if r.get("outcome") == "NEUTRAL_DRAW")
        n = len(rows)
        n_dir = hits + fails
        matrix[hname] = {
            "n_scored": n,
            "directional_hit_rate": round(hits / n_dir, 4) if n_dir else None,
            "soft_hit_rate": round((hits + 0.5 * neutral) / n, 4) if n else None,
        }

    ranked = sorted(
        MYEONGNI_GRID.keys(),
        key=lambda h: float((matrix.get(h) or {}).get("soft_hit_rate") or -1.0),
        reverse=True,
    )
    contract_rank = ranked.index(contract_horizon) + 1 if contract_horizon in ranked else None
    contract_soft = (matrix.get(contract_horizon) or {}).get("soft_hit_rate")
    best_h = ranked[0] if ranked else None
    best_soft = (matrix.get(best_h) or {}).get("soft_hit_rate") if best_h else None

    return {
        "n_eval_dates": len(eval_dates),
        "horizon_grid": MYEONGNI_GRID,
        "contract_horizon": contract_horizon,
        "rate_by_horizon": matrix,
        "ranked_by_soft_hit_rate": ranked,
        "contract_horizon_rank": contract_rank,
        "contract_soft_hit_rate": contract_soft,
        "best_horizon": best_h,
        "best_soft_hit_rate": best_soft,
        "contract_is_best": best_h == contract_horizon,
        "soft_delta_best_minus_contract": (
            round(float(best_soft) - float(contract_soft), 4)
            if best_soft is not None and contract_soft is not None
            else None
        ),
        "verdict_ko": (
            f"계약 {contract_horizon}이 그리드 1위"
            if best_h == contract_horizon
            else f"계약 {contract_horizon}은 {contract_rank}위 · 최적={best_h}"
        ),
    }


def run_v2_leg(
    *,
    instrument: str,
    csv_path: Path,
    date_from: str | None,
    date_to: str | None,
    neutral_bps: float,
    myeongni_jsonl: Path,
    sasang_jsonl: Path,
    logos_lens: Path,
    myeongni_momentum_window: int,
    min_n: int,
    min_soft_delta: float,
    intensity_horizon_days: int,
    write_logos_jsonl: bool,
) -> dict[str, Any]:
    v1_leg = v1.run_eval(
        instrument=instrument,
        csv_path=csv_path,
        date_from=date_from,
        date_to=date_to,
        neutral_bps=neutral_bps,
        neutral_band=0.06,
        myeongni_jsonl=myeongni_jsonl,
        sasang_jsonl=sasang_jsonl,
        logos_lens=logos_lens,
        panel_csv=v1.DEFAULT_PANEL,
        myeongni_momentum_window=myeongni_momentum_window,
        min_n=min_n,
        min_soft_delta=min_soft_delta,
    )

    closes = v1._load_closes(csv_path)
    trading_days = sorted(closes.keys())
    if date_from:
        trading_days = [d for d in trading_days if d >= date_from]
    if date_to:
        trading_days = [d for d in trading_days if d <= date_to]

    labels = v1._build_forward_labels(trading_days, closes, neutral_bps=neutral_bps)
    gate_paths: list[tuple[int, Path]] = [
        (3, MACRO_RISK_LOG),
        (2, FRAGILITY_LOG),
        (1, MACRO_RISK_BACKFILL_LOG),
    ]
    logos_rows = _build_logos_per_date_rows(
        trading_days,
        closes,
        neutral_bps=neutral_bps,
        logos_lens=logos_lens,
        gate_paths=gate_paths,
    )
    if write_logos_jsonl:
        _write_logos_per_date_jsonl(logos_rows, LOGOS_PER_DATE_JSONL)
    logos_by_date = {str(r["session_date"]): r for r in logos_rows}

    sa_by = rows_by_calendar_day(read_jsonl(sasang_jsonl))
    my_by = rows_by_calendar_day(read_jsonl(myeongni_jsonl))
    grid_labels = _build_grid_labels(trading_days, closes, neutral_bps=neutral_bps, horizons=MYEONGNI_GRID)

    macro_cov = _macro_risk_coverage(logos_by_date)
    logos_eval = _eval_logos_variants(
        trading_days=trading_days,
        labels=labels,
        logos_rows_by_date=logos_by_date,
        min_n=min_n,
        min_soft_delta=min_soft_delta,
        macro_risk_coverage=macro_cov,
    )
    sasang_intensity = _eval_sasang_intensity(
        trading_days=trading_days,
        closes=closes,
        sasang_by_day=sa_by,
        intensity_horizon_days=intensity_horizon_days,
        high_pct=75.0,
    )
    myeongni_grid = _eval_myeongni_grid(
        trading_days=trading_days,
        grid_labels=grid_labels,
        myeongni_by_day=my_by,
        myeongni_momentum_window=myeongni_momentum_window,
    )

    v2_supported = (
        logos_eval.get("variants_macro_alignment_pass_effective", 0) >= 1
        and bool(sasang_intensity.get("intensity_pass"))
        and bool(myeongni_grid.get("contract_is_best"))
    )

    return {
        "schema": "three_lens_horizon_empirical_eval_v2_leg",
        "instrument": instrument,
        "v1_direction_eval": {
            "alignment_verdict": v1_leg.get("alignment_verdict"),
            "n_eval_dates": v1_leg.get("n_eval_dates"),
        },
        "logos_per_date_eval": logos_eval,
        "logos_per_date_jsonl": str(LOGOS_PER_DATE_JSONL.relative_to(ROOT)).replace("\\", "/") if write_logos_jsonl else None,
        "sasang_intensity_eval": sasang_intensity,
        "myeongni_horizon_grid": myeongni_grid,
        "v2_composite": {
            "hypothesis_supported_v2": v2_supported,
            "verdict_ko": (
                "v2 확장 실증 일부 충족"
                if v2_supported
                else "v2 확장 실증 미달 — 역할 계약 유지·per-date Logos·강도 라벨 보강 필요"
            ),
        },
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--instrument", choices=("kospi", "btc", "both"), default="kospi")
    ap.add_argument("--date-from", type=str, default="2026-01-01")
    ap.add_argument("--date-to", type=str, default="2026-04-30")
    ap.add_argument("--neutral-bps", type=float, default=5.0)
    ap.add_argument("--myeongni-momentum-window", type=int, default=5)
    ap.add_argument("--intensity-horizon-days", type=int, default=5)
    ap.add_argument("--min-n", type=int, default=20)
    ap.add_argument("--min-soft-delta", type=float, default=0.03)
    ap.add_argument("--no-logos-jsonl", action="store_true")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--artifact-output", type=Path, default=ART_OUT)
    args = ap.parse_args(argv)

    legs: dict[str, Any] = {}
    if args.instrument in ("kospi", "both"):
        legs["kospi"] = run_v2_leg(
            instrument="kospi",
            csv_path=KOSPI_CSV,
            date_from=args.date_from,
            date_to=args.date_to,
            neutral_bps=args.neutral_bps,
            myeongni_jsonl=DEFAULT_MYEONGNI_JSONL,
            sasang_jsonl=DEFAULT_SASANG_JSONL,
            logos_lens=DEFAULT_LOGOS_LENS,
            myeongni_momentum_window=args.myeongni_momentum_window,
            min_n=args.min_n,
            min_soft_delta=args.min_soft_delta,
            intensity_horizon_days=args.intensity_horizon_days,
            write_logos_jsonl=not args.no_logos_jsonl,
        )
    if args.instrument in ("btc", "both"):
        legs["btc"] = run_v2_leg(
            instrument="btc",
            csv_path=BTC_CSV,
            date_from=args.date_from,
            date_to=args.date_to,
            neutral_bps=args.neutral_bps,
            myeongni_jsonl=DEFAULT_MYEONGNI_JSONL,
            sasang_jsonl=DEFAULT_SASANG_JSONL,
            logos_lens=DEFAULT_LOGOS_LENS,
            myeongni_momentum_window=args.myeongni_momentum_window,
            min_n=args.min_n,
            min_soft_delta=args.min_soft_delta,
            intensity_horizon_days=args.intensity_horizon_days,
            write_logos_jsonl=False,
        )

    doc = {
        "schema": "three_lens_horizon_empirical_eval_v2",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "date_from": args.date_from,
        "date_to": args.date_to,
        "legs": legs,
        "summary": {
            k: {
                "v1_supported": legs[k]["v1_direction_eval"]["alignment_verdict"]["hypothesis_supported"],
                "v2_supported": legs[k]["v2_composite"]["hypothesis_supported_v2"],
                "verdict_ko": legs[k]["v2_composite"]["verdict_ko"],
                "myeongni_best": legs[k]["myeongni_horizon_grid"].get("best_horizon"),
                "logos_best_variant": legs[k]["logos_per_date_eval"].get("best_variant_by_macro_soft"),
            }
            for k in legs
        },
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.artifact_output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    art = legs.get("kospi") or doc
    args.artifact_output.write_text(json.dumps(art, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    k = legs.get("kospi", {})
    print(
        f"WROTE: {args.output.resolve()} v2_supported={k.get('v2_composite', {}).get('hypothesis_supported_v2')} "
        f"myeongni_best={k.get('myeongni_horizon_grid', {}).get('best_horizon')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
