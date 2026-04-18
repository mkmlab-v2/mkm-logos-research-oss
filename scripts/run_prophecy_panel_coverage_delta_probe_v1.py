# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.85, L:0.85, K:0.45, M:0.35}
# Balance: 90
# Purpose: SSOT probe — instrument leg coverage, prior-momentum lane, stress proxy, lens-broadcast delta
# Keywords: prophecy, btrack, coverage, delta, kospi, btc, prior return
#!/usr/bin/env python3
"""B-track panel coverage + directional-hit delta probe (research-only).

Summarizes what is already measured elsewhere (to avoid duplicate narratives) and runs a
small set of *additional* lanes on the same ``btrack_prophecy_score_v1`` ``rows[]``:

- baseline (all legs)
- per-leg baselines (kospi / btc) when rows exist
- ``prior_day_momentum_direction_v0``: replace ``predicted_direction`` with the sign of the
  prior *completed* daily return (same causal window as ``run_prophecy_restoration_spike``;
  not A-track, not live trading).
- ``stress_bear_to_neutral_v0``: bear→neutral when eval year is in the 4D year-map stress set
- ``broadcast_fused_lenses_v0``: confidence-weighted vote from latest independent lens JSONs
  (constant across dates until per-date lens panels exist).

Output: ``docs/final/artifacts/prophecy_panel_coverage_delta_probe_v1_latest.json``
Schema: ``prophecy_panel_coverage_delta_probe_v1``
"""

from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCORE = ROOT / "docs" / "final" / "artifacts" / "btrack_prophecy_score_latest.json"
DEFAULT_KOSPI_CSV = ROOT / "research" / "market_data" / "kospi_daily_external_yf.csv"
DEFAULT_BTC_CSV = ROOT / "research" / "market_data" / "btc_daily_external_yf.csv"
DEFAULT_YEAR_MAP = ROOT / "docs" / "final" / "artifacts" / "4d_to_ohaeng_regime_year_map_sample_v1.json"
DEFAULT_MYEONGNI = ROOT / "docs" / "final" / "artifacts" / "myeongni_independent_lens_latest.json"
DEFAULT_SASANG = ROOT / "docs" / "final" / "artifacts" / "sasang_independent_lens_latest.json"
DEFAULT_LOGOS = ROOT / "docs" / "final" / "artifacts" / "logos_independent_lens_latest.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "prophecy_panel_coverage_delta_probe_v1_latest.json"
SCHEMA = "prophecy_panel_coverage_delta_probe_v1"
VALID = {"bull", "bear", "neutral"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        o = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return o if isinstance(o, dict) else None


def _prior_completed_daily_return_by_eval_date(csv_path: Path) -> dict[str, float]:
    """Same causal map as ``run_prophecy_restoration_spike._prior_completed_daily_return_by_eval_date``."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from scripts.logos_shadow_eval_lib import load_kospi_yf_rows

    rows = load_kospi_yf_rows(csv_path)
    if len(rows) < 3:
        return {}
    out: dict[str, float] = {}
    for i in range(2, len(rows)):
        ed = str(rows[i]["date"])[:10]
        try:
            c1 = float(rows[i - 1]["close"])
            c2 = float(rows[i - 2]["close"])
        except (TypeError, ValueError):
            continue
        if c2 == 0.0:
            continue
        out[ed] = (c1 - c2) / c2
    return out


def _stress_years(year_map: Path) -> set[int]:
    out: set[int] = set()
    doc = _load_json(year_map)
    if not doc:
        return out
    rows = doc.get("rows")
    if not isinstance(rows, list):
        return out
    for r in rows:
        if not isinstance(r, dict):
            continue
        try:
            sy = int(r.get("start_year"))
            ey = int(r.get("end_year", sy))
        except (TypeError, ValueError):
            continue
        lo, hi = min(sy, ey), max(sy, ey)
        for y in range(lo, hi + 1):
            out.add(y)
    return out


def _eval_year(eval_date: str) -> int | None:
    s = str(eval_date or "").strip()
    if len(s) < 4 or not s[:4].isdigit():
        return None
    return int(s[:4])


def _actual_direction_from_return(ret: float, neutral_bps: float) -> str:
    thr = float(neutral_bps) / 10000.0
    if abs(ret) < thr:
        return "neutral"
    return "bull" if ret > 0.0 else "bear"


def _pick_sign(v: float) -> str:
    if v > 0:
        return "bull"
    if v < 0:
        return "bear"
    return "neutral"


def _load_lens(path: Path, fallback_id: str) -> dict[str, Any]:
    doc = _load_json(path)
    if not doc:
        return {
            "lens_id": fallback_id,
            "available": False,
            "direction_sign": "neutral",
            "confidence": 0.0,
        }
    scores = doc.get("scores") if isinstance(doc.get("scores"), dict) else {}
    ds = float(scores.get("direction_score", 0.0))
    cf = float(scores.get("confidence", 0.0))
    return {
        "lens_id": str(doc.get("lens_id") or fallback_id),
        "available": True,
        "direction_sign": _pick_sign(ds),
        "confidence": max(0.0, min(1.0, cf)),
    }


def _hit_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    hits = 0
    n = 0
    for r in rows:
        pd = str(r.get("predicted_direction") or "").strip().lower()
        ad = str(r.get("actual_direction") or "").strip().lower()
        if not pd or not ad:
            continue
        if pd not in VALID or ad not in VALID:
            continue
        n += 1
        if pd == ad:
            hits += 1
    return {
        "price_directional_hit_rate": round(hits / n, 6) if n else None,
        "n_evaluated": n,
        "price_hits": hits,
    }


def _filter_leg(rows: list[dict[str, Any]], leg: str) -> list[dict[str, Any]]:
    leg_l = leg.strip().lower()
    return [r for r in rows if isinstance(r, dict) and str(r.get("instrument") or "").strip().lower() == leg_l]


def _apply_prior_momentum(
    rows: list[dict[str, Any]],
    *,
    prior_by_date: dict[str, float],
    neutral_bps: float,
) -> tuple[list[dict[str, Any]], int, int]:
    out = deepcopy(rows)
    changed = 0
    missing = 0
    for r in out:
        ed = str(r.get("eval_date") or "").strip()[:10]
        pr = prior_by_date.get(ed)
        if pr is None:
            missing += 1
            continue
        new_pred = _actual_direction_from_return(pr, neutral_bps)
        old = str(r.get("predicted_direction") or "").strip().lower()
        if old != new_pred:
            changed += 1
        r["predicted_direction"] = new_pred
        r["lane_note"] = "prior_day_momentum_direction_v0"
    return out, changed, missing


def _apply_stress_bear_neutral(rows: list[dict[str, Any]], stress: set[int]) -> tuple[list[dict[str, Any]], int]:
    out = deepcopy(rows)
    changed = 0
    for r in out:
        pred = str(r.get("predicted_direction") or "").strip().lower()
        ed = str(r.get("eval_date") or "").strip()[:10]
        y = _eval_year(ed)
        if y is not None and y in stress and pred == "bear":
            r["predicted_direction"] = "neutral"
            r["lane_note"] = "stress_bear_to_neutral_v0"
            changed += 1
    return out, changed


def _apply_broadcast_fused(
    rows: list[dict[str, Any]],
    lenses: list[dict[str, Any]],
    min_confidence: float,
) -> tuple[list[dict[str, Any]], int, dict[str, Any]]:
    votes = {"bull": 0.0, "bear": 0.0}
    used: list[dict[str, Any]] = []
    for lens in lenses:
        if not lens["available"] or lens["confidence"] < min_confidence:
            continue
        s = lens["direction_sign"]
        if s in ("bull", "bear"):
            votes[s] += float(lens["confidence"])
            used.append({"lens_id": lens["lens_id"], "sign": s, "confidence": lens["confidence"]})
    if votes["bull"] == votes["bear"] == 0.0:
        return deepcopy(rows), 0, {"fused_sign": "neutral", "votes": votes, "used_lenses": used}
    fused = "bull" if votes["bull"] > votes["bear"] else "bear"
    out = deepcopy(rows)
    ch = 0
    for r in out:
        old = str(r.get("predicted_direction") or "").strip().lower()
        if old in VALID and old != fused:
            ch += 1
        r["predicted_direction"] = fused
        r["lane_note"] = "broadcast_fused_lenses_v0"
    return out, ch, {"fused_sign": fused, "votes": votes, "used_lenses": used}


def main() -> int:
    ap = argparse.ArgumentParser(description="Prophecy panel coverage + delta probe (B-track).")
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--kospi-csv", type=Path, default=DEFAULT_KOSPI_CSV)
    ap.add_argument("--btc-csv", type=Path, default=DEFAULT_BTC_CSV, help="Optional; defaults to repo YF CSV if present.")
    ap.add_argument("--year-map-json", type=Path, default=DEFAULT_YEAR_MAP)
    ap.add_argument("--myeongni-lens", type=Path, default=DEFAULT_MYEONGNI)
    ap.add_argument("--sasang-lens", type=Path, default=DEFAULT_SASANG)
    ap.add_argument("--logos-lens", type=Path, default=DEFAULT_LOGOS)
    ap.add_argument("--min-lens-confidence", type=float, default=0.2)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    doc = _load_json(args.score_json)
    if not doc or not isinstance(doc.get("rows"), list):
        raise SystemExit(f"invalid score json: {args.score_json}")
    rows_all = [r for r in doc["rows"] if isinstance(r, dict)]
    neutral_bps = float(doc.get("neutral_bps") or doc.get("inputs", {}).get("neutral_bps") or 5.0)

    btc_csv = args.btc_csv if args.btc_csv.is_file() else None

    counts: dict[str, int] = {}
    for r in rows_all:
        inst = str(r.get("instrument") or "unknown").strip().lower()
        counts[inst] = counts.get(inst, 0) + 1

    prior_map: dict[str, float] = {}
    if args.kospi_csv.is_file():
        prior_map = _prior_completed_daily_return_by_eval_date(args.kospi_csv)

    stress = _stress_years(args.year_map_json)
    lenses = [
        _load_lens(args.myeongni_lens, "myeongni"),
        _load_lens(args.sasang_lens, "sasang"),
        _load_lens(args.logos_lens, "logos"),
    ]

    base = _hit_metrics(rows_all)
    base_rate = float(base["price_directional_hit_rate"] or 0.0)

    lanes: list[dict[str, Any]] = []

    def add_lane(lane_id: str, subset: list[dict[str, Any]], metrics: dict[str, Any], **extra: Any) -> None:
        rate = metrics.get("price_directional_hit_rate")
        dr = round(float(rate or 0.0) - base_rate, 6) if subset is rows_all and rate is not None else None
        row: dict[str, Any] = {"lane_id": lane_id, "row_count": len(subset), "metrics": metrics, "delta_vs_all_baseline": dr}
        row.update(extra)
        lanes.append(row)

    add_lane("baseline_all", rows_all, _hit_metrics(rows_all))

    for leg in ("kospi", "btc"):
        sub = _filter_leg(rows_all, leg)
        if sub:
            add_lane(f"baseline_{leg}_leg", sub, _hit_metrics(sub))

    pm_rows, pm_ch, pm_miss = _apply_prior_momentum(rows_all, prior_by_date=prior_map, neutral_bps=neutral_bps)
    add_lane(
        "prior_day_momentum_direction_v0",
        rows_all,
        _hit_metrics(pm_rows),
        changed_rows=pm_ch,
        missing_prior_completed_return_rows=pm_miss,
        neutral_bps=neutral_bps,
    )

    st_rows, st_ch = _apply_stress_bear_neutral(rows_all, stress)
    add_lane(
        "stress_bear_to_neutral_v0",
        rows_all,
        _hit_metrics(st_rows),
        changed_rows=st_ch,
        stress_year_count=len(stress),
    )

    fus_rows, fus_ch, fus_meta = _apply_broadcast_fused(rows_all, lenses, args.min_lens_confidence)
    add_lane(
        "broadcast_fused_lenses_v0",
        rows_all,
        _hit_metrics(fus_rows),
        changed_rows=fus_ch,
        fused_meta=fus_meta,
    )

    audit = {
        "adjacent_or_duplicate_measurement_paths": [
            "scripts/run_prophecy_restoration_spike.py — overlay ablation on same rows (prior shock / stress).",
            "scripts/run_prophecy_fusion_ablation_spike.py — broadcast lens vote + stress proxy deltas.",
            "docs/final/artifacts/prophecy_eval_comparison_report_latest.json — fixed-direction vs walk-forward (different contract; coverage warnings).",
            "scripts/spike_gematria_myeongri_blend_v0.py — geometric blend; explicitly not prediction accuracy.",
            "scripts/run_gematria_4d_gate.py / scripts/run_btrack_fusion_gate.py — alignment/uplift gates; not OHLCV directional hit.",
        ],
        "btc_leg_note": (
            "If hypothesis instrument is multi but btc leg rows are absent, rebuild with "
            "`py scripts/build_btrack_prophecy_score_from_ohlcv.py --btc-csv <YF-style daily>` "
            f"(repo sample: {DEFAULT_BTC_CSV})."
        ),
    }

    best = sorted(
        [x for x in lanes if x["lane_id"] not in ("baseline_all",)],
        key=lambda x: (float(x["metrics"].get("price_directional_hit_rate") or -1.0), -int(x.get("changed_rows", 0))),
        reverse=True,
    )

    out = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "inputs": {
            "score_json": str(args.score_json),
            "kospi_csv": str(args.kospi_csv),
            "btc_csv": str(btc_csv) if btc_csv else None,
            "year_map_json": str(args.year_map_json),
            "min_lens_confidence": args.min_lens_confidence,
        },
        "score_summary": {
            "neutral_bps": neutral_bps,
            "instrument_row_counts": counts,
            "has_btc_rows": counts.get("btc", 0) > 0,
        },
        "baseline_all": {"lane_id": "baseline_all", "metrics": base},
        "lanes": lanes,
        "best_non_baseline_lane": best[0] if best else None,
        "audit": audit,
        "recommended_next_steps": [
            "Rebuild ``btrack_prophecy_score_latest.json`` with ``--btc-csv`` so ``baseline_btc_leg`` exists for BTC-specific Δ.",
            "Replace broadcast lens artifacts with **per-eval_date** lens panels (JSONL keyed by eval_date) — current *_latest.json tails are global.",
            "Keep one primary price metric: ``eval_prophecy_hit_rate_v1.py --run-mode price`` on the same score snapshot used here.",
        ],
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    if best:
        b = best[0]
        print(
            f"BASE(all) hit={base['price_directional_hit_rate']} n={base['n_evaluated']} | "
            f"TOP {b['lane_id']} hit={b['metrics'].get('price_directional_hit_rate')}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
