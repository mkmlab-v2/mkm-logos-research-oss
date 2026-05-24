#!/usr/bin/env python3
"""Attribute B-track neutral predictions (margin band vs low-confidence gate).

Reads per-date direction rows (reports/btrack_ensemble_per_date_directions_v1_latest.json).
Writes reports/btrack_neutral_attribution_v1_latest.json — research_only [HYPO].
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

from scripts.btrack_direction_confidence_gate_v1 import min_direction_confidence_threshold

DEFAULT_PER_DATE = ROOT / "reports" / "btrack_ensemble_per_date_directions_v1_latest.json"
DEFAULT_CFG = ROOT / "docs/final/artifacts/btrack_lens_ensemble_v1.json"
DEFAULT_OUT = ROOT / "reports" / "btrack_neutral_attribution_v1_latest.json"
SCHEMA = "btrack_neutral_attribution_v1"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _tie_margin(rules: dict[str, Any]) -> float:
    return max(0.0, _safe_float(rules.get("tie_break_min_margin"), 0.03))


def classify_row(row: dict[str, Any], *, margin: float, conf_thresh: float) -> str:
    pred = str(row.get("predicted_direction") or "").strip().lower()
    if pred in ("bull", "bear"):
        return "directional_call"
    w = _safe_float(row.get("weighted_score"), 0.0)
    conf = _safe_float(row.get("confidence"), 0.0)
    gate = row.get("low_confidence_direction_gate")
    if isinstance(gate, dict) and gate.get("applied"):
        return "low_confidence_gate"
    prelim = str(row.get("preliminary_direction") or "").strip().lower()
    if abs(w) < margin:
        return "margin_band_neutral"
    if prelim in ("bull", "bear") and conf < conf_thresh:
        return "low_confidence_gate_inferred"
    if prelim in ("bull", "bear"):
        return "neutral_after_directional_prelim"
    return "ensemble_neutral_other"


def build_report(
    per_date_doc: dict[str, Any],
    *,
    ensemble_cfg: dict[str, Any],
    eval_path: Path | None = None,
) -> dict[str, Any]:
    rules = ensemble_cfg.get("rules") if isinstance(ensemble_cfg.get("rules"), dict) else {}
    margin = _tie_margin(rules)
    conf_thresh = min_direction_confidence_threshold(rules)
    rows_in = per_date_doc.get("rows") if isinstance(per_date_doc.get("rows"), list) else []
    btc_rows = [
        r for r in rows_in if isinstance(r, dict) and str(r.get("instrument") or "").lower() == "btc"
    ]
    by_reason: dict[str, int] = {}
    detail: list[dict[str, Any]] = []
    for row in btc_rows:
        reason = classify_row(row, margin=margin, conf_thresh=conf_thresh)
        by_reason[reason] = by_reason.get(reason, 0) + 1
        if reason != "directional_call":
            detail.append(
                {
                    "eval_date": row.get("eval_date"),
                    "predicted_direction": row.get("predicted_direction"),
                    "preliminary_direction": row.get("preliminary_direction"),
                    "weighted_score": row.get("weighted_score"),
                    "confidence": row.get("confidence"),
                    "attribution": reason,
                    "low_confidence_gate_applied": bool(
                        (row.get("low_confidence_direction_gate") or {}).get("applied")
                    ),
                }
            )

    n = len(btc_rows)
    n_neutral = sum(1 for r in btc_rows if str(r.get("predicted_direction")).lower() == "neutral")
    n_dir = n - n_neutral
    gate_count = by_reason.get("low_confidence_gate", 0) + by_reason.get(
        "low_confidence_gate_inferred", 0
    )
    margin_count = by_reason.get("margin_band_neutral", 0)

    would_directional_if_lower_thresh: dict[str, int] = {}
    sensitivity_grid = (0.15, 0.18, 0.20, 0.22, 0.25)
    for row in btc_rows:
        if str(row.get("predicted_direction")).lower() != "neutral":
            continue
        prelim = str(row.get("preliminary_direction") or "").strip().lower()
        if prelim not in ("bull", "bear"):
            continue
        conf = _safe_float(row.get("confidence"), 0.0)
        w = _safe_float(row.get("weighted_score"), 0.0)
        if abs(w) < margin:
            continue
        for t in sensitivity_grid:
            if conf >= t:
                key = f"threshold_{t:.2f}"
                would_directional_if_lower_thresh[key] = (
                    would_directional_if_lower_thresh.get(key, 0) + 1
                )
    would_directional_at_20 = would_directional_if_lower_thresh.get("threshold_0.20", 0)
    would_directional_at_18 = would_directional_if_lower_thresh.get("threshold_0.18", 0)
    would_directional_at_15 = would_directional_if_lower_thresh.get("threshold_0.15", 0)

    headline_eval = None
    if eval_path and eval_path.is_file():
        ev = _load_json(eval_path)
        m = ev.get("metrics") if isinstance(ev.get("metrics"), dict) else {}
        headline_eval = {
            "price_directional_hit_rate_all_rows": m.get("price_directional_hit_rate"),
            "price_hit_rate_on_directional_calls": m.get("price_hit_rate_on_directional_calls"),
            "n_directional_calls": m.get("n_directional_calls"),
            "n_neutral_predictions": m.get("n_neutral_predictions"),
        }

    return {
        "schema": SCHEMA,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "inputs": {
            "per_date_json": str(per_date_doc.get("inputs") or DEFAULT_PER_DATE),
            "ensemble_config": str(DEFAULT_CFG),
            "tie_break_min_margin": margin,
            "min_direction_confidence": conf_thresh,
        },
        "summary": {
            "n_btc_eval_dates": n,
            "n_directional_calls": n_dir,
            "n_neutral_predictions": n_neutral,
            "neutral_share": round(n_neutral / n, 6) if n else None,
            "low_confidence_gate_neutrals": gate_count,
            "margin_band_neutrals": margin_count,
            "would_be_directional_if_lower_threshold": would_directional_if_lower_thresh,
            "would_be_directional_if_threshold_0_20": would_directional_at_20,
            "would_be_directional_if_threshold_0_18": would_directional_at_18,
            "would_be_directional_if_threshold_0_15": would_directional_at_15,
            "min_conf_sensitivity_grid": would_directional_if_lower_thresh,
            "dominant_neutral_driver": (
                "low_confidence_gate"
                if gate_count >= margin_count
                else "margin_band"
                if margin_count
                else "mixed_or_other"
            ),
        },
        "counts_by_attribution": dict(sorted(by_reason.items())),
        "neutral_rows": detail,
        "headline_eval_pointer": headline_eval,
        "operator_lines": [
            f"- [MKM-BTRACK-NEUTRAL] BTC {n_dir}/{n} directional "
            f"({n_neutral} neutral); gate≈{gate_count} margin≈{margin_count} "
            f"(min_conf={conf_thresh:.2f}, margin={margin:.3f})",
            (
                f"- [MKM-BTRACK-NEUTRAL] min_conf sensitivity (directional prelim, |w|≥margin): "
                f"0.15→{would_directional_at_15}d, 0.18→{would_directional_at_18}d, "
                f"0.20→{would_directional_at_20}d vs current {int(n_dir)}d "
                "(hypothesis; re-run per-date+score+eval to measure)."
            ),
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--per-date-json", type=Path, default=DEFAULT_PER_DATE)
    ap.add_argument("--ensemble-config", type=Path, default=DEFAULT_CFG)
    ap.add_argument("--eval-json", type=Path, default=ROOT / "docs/final/artifacts/prophecy_hit_rate_eval_latest.json")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--stdout-only", action="store_true")
    args = ap.parse_args()
    if not args.per_date_json.is_file():
        print(f"Missing: {args.per_date_json}", file=sys.stderr)
        return 2
    per_date = _load_json(args.per_date_json)
    cfg = _load_json(args.ensemble_config) if args.ensemble_config.is_file() else {}
    report = build_report(
        per_date,
        ensemble_cfg=cfg,
        eval_path=args.eval_json if args.eval_json.is_file() else None,
    )
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.stdout_only:
        print(text)
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
        print(f"WROTE: {args.output.resolve()}")
        for line in report.get("operator_lines") or []:
            print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
