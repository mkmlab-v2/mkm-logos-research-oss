#!/usr/bin/env python3
"""Sweep min-confidence and score deadzone HOLD filters on headline score panel (B-track).

Joins per-date ensemble metadata (confidence, weighted_score) to score rows, then reports:
- hit_rate_all (no filter)
- hit_rate_active (rows passing filters; ambiguous -> skipped)
- coverage_active

research_only — does not mutate Track A or enable live trading.
"""
from __future__ import annotations

import argparse
import itertools
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCORE = ROOT / "reports" / "btrack_prophecy_score_recommended_eval_chain_v1_latest.json"
DEFAULT_PER_DATE = ROOT / "reports" / "btrack_ensemble_per_date_directions_180d_v1_latest.json"
DEFAULT_OUT = ROOT / "reports" / "prophecy_headline_deadzone_hold_sweep_v1_latest.json"
SCHEMA = "prophecy_headline_deadzone_hold_sweep_v1"
VALID = frozenset({"bull", "bear", "neutral"})


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


def _metrics_active(
    rows: list[dict[str, Any]],
    *,
    min_confidence: float,
    score_abs_deadzone: float,
    per_date_index: dict[tuple[str, str], dict[str, Any]],
) -> dict[str, Any]:
    n_total = len(rows)
    n_active = 0
    n_skipped_low_conf = 0
    n_skipped_deadzone = 0
    n_skipped_missing_meta = 0
    n_btc_meta_fallback = 0
    hits = 0
    for r in rows:
        inst = str(r.get("instrument") or "btc").strip().lower()
        ed = str(r.get("eval_date") or "")[:10]
        actual = str(r.get("actual_direction") or "").strip().lower()
        if actual not in VALID:
            continue
        meta, lookup_mode = _lookup_per_date_meta(per_date_index, eval_date=ed, instrument=inst)
        if not meta:
            n_skipped_missing_meta += 1
            continue
        if lookup_mode == "btc_fallback_same_date":
            n_btc_meta_fallback += 1
        conf = meta.get("confidence")
        try:
            conf_f = float(conf) if conf is not None else 0.0
        except (TypeError, ValueError):
            conf_f = 0.0
        if conf_f < min_confidence:
            n_skipped_low_conf += 1
            continue
        ws = meta.get("weighted_score")
        try:
            ws_f = float(ws) if ws is not None else 0.0
        except (TypeError, ValueError):
            ws_f = 0.0
        if score_abs_deadzone > 0.0 and abs(ws_f) < score_abs_deadzone:
            n_skipped_deadzone += 1
            continue
        pred = str(r.get("predicted_direction") or "").strip().lower()
        if pred not in VALID or pred == "neutral":
            n_skipped_deadzone += 1
            continue
        n_active += 1
        if pred == actual:
            hits += 1
    rate_active = round(hits / n_active, 6) if n_active else None
    coverage = round(n_active / n_total, 6) if n_total else None
    return {
        "price_directional_hit_rate_active": rate_active,
        "price_directional_hit_rate_all": None,
        "n_total_rows": n_total,
        "n_active": n_active,
        "n_skipped_low_confidence": n_skipped_low_conf,
        "n_skipped_score_deadzone_or_neutral_pred": n_skipped_deadzone,
        "n_skipped_missing_per_date_meta": n_skipped_missing_meta,
        "n_kospi_rows_used_btc_meta_fallback": n_btc_meta_fallback,
        "price_hits_active": hits,
        "coverage_active": coverage,
    }


def _metrics_all(rows: list[dict[str, Any]]) -> dict[str, Any]:
    n = 0
    h = 0
    for r in rows:
        pd = str(r.get("predicted_direction") or "").strip().lower()
        ad = str(r.get("actual_direction") or "").strip().lower()
        if pd not in VALID or ad not in VALID:
            continue
        n += 1
        if pd == ad:
            h += 1
    rate = round(h / n, 6) if n else None
    return {
        "price_directional_hit_rate_all": rate,
        "n_evaluated_all": n,
        "price_hits_all": h,
    }


def _per_date_index(path: Path) -> dict[tuple[str, str], dict[str, Any]]:
    doc = _load_json(path)
    if not doc:
        return {}
    rows = doc.get("rows") if isinstance(doc.get("rows"), list) else []
    out: dict[tuple[str, str], dict[str, Any]] = {}
    for r in rows:
        if not isinstance(r, dict):
            continue
        ed = str(r.get("eval_date") or "")[:10]
        inst = str(r.get("instrument") or "btc").strip().lower()
        if ed:
            out[(ed, inst)] = r
    return out


def _lookup_per_date_meta(
    per_date_index: dict[tuple[str, str], dict[str, Any]],
    *,
    eval_date: str,
    instrument: str,
) -> tuple[dict[str, Any] | None, str]:
    """Return (meta, lookup_mode). KOSPI dual-leg rows reuse BTC same-date meta when needed."""
    inst = instrument.strip().lower()
    direct = per_date_index.get((eval_date, inst))
    if direct:
        return direct, "direct"
    if inst == "kospi":
        fb = per_date_index.get((eval_date, "btc"))
        if fb:
            return fb, "btc_fallback_same_date"
    return None, "missing"


def main() -> int:
    ap = argparse.ArgumentParser(description="Headline deadzone + confidence HOLD sweep (B-track).")
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--per-date-json", type=Path, default=DEFAULT_PER_DATE)
    ap.add_argument(
        "--min-confidence-grid",
        type=str,
        default="0.0,0.15,0.18,0.22,0.25,0.30,0.35",
    )
    ap.add_argument(
        "--score-abs-deadzone-grid",
        type=str,
        default="0.0,0.05,0.10,0.12,0.15,0.18,0.20",
    )
    ap.add_argument("--min-coverage-active", type=float, default=0.55)
    ap.add_argument("--top-k", type=int, default=15)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    score_doc = _load_json(args.score_json)
    if not score_doc or not isinstance(score_doc.get("rows"), list):
        raise SystemExit(f"invalid score json: {args.score_json}")
    rows = [r for r in score_doc["rows"] if isinstance(r, dict)]
    if not rows:
        raise SystemExit("score json has no rows")

    pdx = _per_date_index(args.per_date_json)
    baseline_all = _metrics_all(rows)
    base_rate = float(baseline_all.get("price_directional_hit_rate_all") or 0.0)

    conf_grid = [float(x.strip()) for x in args.min_confidence_grid.split(",") if x.strip()]
    dz_grid = [float(x.strip()) for x in args.score_abs_deadzone_grid.split(",") if x.strip()]

    try:
        from evolution_auto_apply_allowlist_v1 import assert_headline_gate_sweep_allowed

        for mc in conf_grid:
            for dz in dz_grid:
                assert_headline_gate_sweep_allowed(min_confidence=mc, score_abs_deadzone=dz)
    except (ImportError, ValueError) as exc:
        raise SystemExit(f"evolution allowlist gate: {exc}") from exc

    candidates: list[dict[str, Any]] = []
    for min_conf, score_dz in itertools.product(conf_grid, dz_grid):
        m = _metrics_active(
            rows,
            min_confidence=min_conf,
            score_abs_deadzone=score_dz,
            per_date_index=pdx,
        )
        m["price_directional_hit_rate_all"] = baseline_all.get("price_directional_hit_rate_all")
        rate_a = float(m.get("price_directional_hit_rate_active") or 0.0)
        cov = float(m.get("coverage_active") or 0.0)
        candidates.append(
            {
                "params": {
                    "min_confidence": min_conf,
                    "score_abs_deadzone": score_dz,
                },
                "metrics": m,
                "delta_vs_baseline_all": round(rate_a - base_rate, 6),
                "passes_50pct_active": rate_a >= 0.50,
                "passes_coverage_floor": cov >= float(args.min_coverage_active),
                "passes_both": rate_a >= 0.50 and cov >= float(args.min_coverage_active),
            }
        )

    ranked = sorted(
        candidates,
        key=lambda x: (
            1 if x.get("passes_both") else 0,
            float((x.get("metrics") or {}).get("price_directional_hit_rate_active") or -1.0),
            float((x.get("metrics") or {}).get("coverage_active") or 0.0),
        ),
        reverse=True,
    )
    best = ranked[0] if ranked else None
    best_pass = next((c for c in ranked if c.get("passes_both")), None)

    out = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "boundary_ack": True,
        "inputs": {
            "score_json": str(args.score_json),
            "per_date_json": str(args.per_date_json),
            "min_confidence_grid": conf_grid,
            "score_abs_deadzone_grid": dz_grid,
            "min_coverage_active_floor": float(args.min_coverage_active),
            "per_date_meta_rows": len(pdx),
        },
        "baseline_all": baseline_all,
        "best_by_active_hit_rate": best,
        "best_passing_50_and_coverage": best_pass,
        "top_candidates": ranked[: max(1, int(args.top_k))],
        "note": (
            "active hit rate excludes low-confidence and low |weighted_score| rows; "
            "does not promote Track A or live trading."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    if best:
        print(
            f"BASE_ALL={baseline_all.get('price_directional_hit_rate_all')} "
            f"BEST_ACTIVE={best['metrics'].get('price_directional_hit_rate_active')} "
            f"cov={best['metrics'].get('coverage_active')} passes_both={best.get('passes_both')}"
        )
    if best_pass and best_pass is not best:
        print(
            f"BEST_PASS_50_COV ACTIVE={best_pass['metrics'].get('price_directional_hit_rate_active')} "
            f"params={best_pass.get('params')}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
