# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.8, L:0.8, K:0.4, M:0.3}
# Balance: 90
# Purpose: B-track ablation for lens-driven prophecy directional deltas
# Keywords: prophecy, ablation, fusion, myeongni, logos, sasang, 4d
#!/usr/bin/env python3
"""Run B-track prophecy fusion ablation spike and emit delta report.

This script keeps A-track fully untouched. It measures directional-hit deltas on the
existing `btrack_prophecy_score_v1 rows[]` panel under simple policy overlays:

- base: untouched predictions
- lens_myeongni / lens_sasang / lens_logos: force non-neutral lens sign (if confident)
- fused_lenses: confidence-weighted consensus sign from lens artifacts
- regime_4d_stress_proxy: bear->neutral on stress years from 4D year-map sample

Output schema: `prophecy_fusion_ablation_spike_v1`
"""
from __future__ import annotations

import argparse
import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCORE = ROOT / "docs" / "final" / "artifacts" / "btrack_prophecy_score_latest.json"
DEFAULT_MYEONGNI = ROOT / "docs" / "final" / "artifacts" / "myeongni_independent_lens_latest.json"
DEFAULT_SASANG = ROOT / "docs" / "final" / "artifacts" / "sasang_independent_lens_latest.json"
DEFAULT_LOGOS = ROOT / "docs" / "final" / "artifacts" / "logos_independent_lens_latest.json"
DEFAULT_YEAR_MAP = ROOT / "docs" / "final" / "artifacts" / "4d_to_ohaeng_regime_year_map_sample_v1.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "prophecy_fusion_ablation_spike_latest.json"
SCHEMA = "prophecy_fusion_ablation_spike_v1"
VALID = {"bull", "bear", "neutral"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def _pick_sign(v: float) -> str:
    if v > 0:
        return "bull"
    if v < 0:
        return "bear"
    return "neutral"


def _load_lens(path: Path, fallback_id: str) -> dict[str, Any]:
    doc = _read_json(path)
    if not doc:
        return {
            "lens_id": fallback_id,
            "available": False,
            "direction_sign": "neutral",
            "confidence": 0.0,
            "path": str(path),
        }
    scores = doc.get("scores") if isinstance(doc.get("scores"), dict) else {}
    score = float(scores.get("direction_score", 0.0))
    confidence = max(0.0, min(1.0, float(scores.get("confidence", 0.0))))
    return {
        "lens_id": str(doc.get("lens_id") or fallback_id),
        "available": True,
        "direction_sign": _pick_sign(score),
        "confidence": confidence,
        "path": str(path),
    }


def _stress_years(year_map: Path) -> set[int]:
    out: set[int] = set()
    doc = _read_json(year_map)
    if not doc:
        return out
    rows = doc.get("rows")
    if not isinstance(rows, list):
        return out
    for row in rows:
        if not isinstance(row, dict):
            continue
        try:
            s = int(row.get("start_year"))
            e = int(row.get("end_year", s))
        except (TypeError, ValueError):
            continue
        lo, hi = min(s, e), max(s, e)
        for y in range(lo, hi + 1):
            out.add(y)
    return out


def _hit_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    hits = 0
    n = 0
    for row in rows:
        pred = str(row.get("predicted_direction") or "").strip().lower()
        actual = str(row.get("actual_direction") or "").strip().lower()
        if pred not in VALID or actual not in VALID:
            continue
        n += 1
        if pred == actual:
            hits += 1
    return {
        "price_directional_hit_rate": round(hits / n, 6) if n else None,
        "n_evaluated": n,
        "price_hits": hits,
    }


def _apply_force_sign(rows: list[dict[str, Any]], sign: str) -> tuple[list[dict[str, Any]], int]:
    if sign not in VALID or sign == "neutral":
        return deepcopy(rows), 0
    out = deepcopy(rows)
    changed = 0
    for row in out:
        pred = str(row.get("predicted_direction") or "").strip().lower()
        if pred in VALID and pred != sign:
            row["predicted_direction"] = sign
            changed += 1
    return out, changed


def _apply_fused_sign(
    rows: list[dict[str, Any]],
    lenses: list[dict[str, Any]],
    min_confidence: float,
) -> tuple[list[dict[str, Any]], int, dict[str, Any]]:
    votes = {"bull": 0.0, "bear": 0.0}
    used = []
    for lens in lenses:
        if not lens["available"]:
            continue
        if lens["confidence"] < min_confidence:
            continue
        sign = lens["direction_sign"]
        if sign in ("bull", "bear"):
            votes[sign] += float(lens["confidence"])
            used.append({"lens_id": lens["lens_id"], "sign": sign, "confidence": lens["confidence"]})
    if votes["bull"] == votes["bear"] == 0.0:
        return deepcopy(rows), 0, {"fused_sign": "neutral", "votes": votes, "used_lenses": used}
    fused_sign = "bull" if votes["bull"] > votes["bear"] else "bear"
    out_rows, changed = _apply_force_sign(rows, fused_sign)
    return out_rows, changed, {"fused_sign": fused_sign, "votes": votes, "used_lenses": used}


def _apply_regime_stress_proxy(rows: list[dict[str, Any]], stress_years: set[int]) -> tuple[list[dict[str, Any]], int]:
    out = deepcopy(rows)
    changed = 0
    for row in out:
        pred = str(row.get("predicted_direction") or "").strip().lower()
        eval_date = str(row.get("eval_date") or "").strip()
        if pred != "bear" or len(eval_date) < 4:
            continue
        try:
            year = int(eval_date[:4])
        except ValueError:
            continue
        if year in stress_years:
            row["predicted_direction"] = "neutral"
            changed += 1
    return out, changed


def main() -> int:
    ap = argparse.ArgumentParser(description="B-track fusion ablation spike for prophecy directional hit-rate deltas.")
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--myeongni", type=Path, default=DEFAULT_MYEONGNI)
    ap.add_argument("--sasang", type=Path, default=DEFAULT_SASANG)
    ap.add_argument("--logos", type=Path, default=DEFAULT_LOGOS)
    ap.add_argument("--year-map", type=Path, default=DEFAULT_YEAR_MAP)
    ap.add_argument("--min-lens-confidence", type=float, default=0.2)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    score_doc = _read_json(args.score_json)
    if not score_doc:
        raise SystemExit(f"Missing or invalid score JSON: {args.score_json}")
    rows = score_doc.get("rows")
    if not isinstance(rows, list):
        raise SystemExit(f"Missing rows[] in score JSON: {args.score_json}")

    lens_rows = [
        _load_lens(args.myeongni, "myeongni"),
        _load_lens(args.sasang, "sasang"),
        _load_lens(args.logos, "logos"),
    ]
    base_metrics = _hit_metrics(rows)
    base_rate = float(base_metrics["price_directional_hit_rate"] or 0.0)

    scenarios: list[dict[str, Any]] = []

    for lane_id, lens_id in (
        ("lens_myeongni", "myeongni"),
        ("lens_sasang", "sasang"),
        ("lens_logos", "logos"),
    ):
        lens = next((x for x in lens_rows if x["lens_id"] == lens_id), None)
        sign = lens["direction_sign"] if lens else "neutral"
        tuned_rows, changed = _apply_force_sign(rows, sign)
        metrics = _hit_metrics(tuned_rows)
        scenarios.append(
            {
                "lane_id": lane_id,
                "policy": "force_non_neutral_lens_sign",
                "lens_sign": sign,
                "changed_rows": changed,
                "metrics": metrics,
                "delta_hit_rate": round(float(metrics["price_directional_hit_rate"] or 0.0) - base_rate, 6),
            }
        )

    fused_rows, fused_changed, fused_meta = _apply_fused_sign(rows, lens_rows, args.min_lens_confidence)
    fused_metrics = _hit_metrics(fused_rows)
    scenarios.append(
        {
            "lane_id": "fused_lenses",
            "policy": "confidence_weighted_lens_vote",
            "changed_rows": fused_changed,
            "fused_meta": fused_meta,
            "metrics": fused_metrics,
            "delta_hit_rate": round(float(fused_metrics["price_directional_hit_rate"] or 0.0) - base_rate, 6),
        }
    )

    stress = _stress_years(args.year_map)
    stress_rows, stress_changed = _apply_regime_stress_proxy(rows, stress)
    stress_metrics = _hit_metrics(stress_rows)
    scenarios.append(
        {
            "lane_id": "regime_4d_stress_proxy",
            "policy": "bear_to_neutral_if_eval_year_in_stress_map",
            "changed_rows": stress_changed,
            "stress_year_count": len(stress),
            "metrics": stress_metrics,
            "delta_hit_rate": round(float(stress_metrics["price_directional_hit_rate"] or 0.0) - base_rate, 6),
        }
    )

    best = sorted(
        scenarios,
        key=lambda x: (x.get("delta_hit_rate", -999.0), -int(x.get("changed_rows", 0))),
        reverse=True,
    )[0]

    out = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "promotion_ready": False,
        "inputs": {
            "score_json": str(args.score_json),
            "year_map": str(args.year_map),
            "min_lens_confidence": args.min_lens_confidence,
        },
        "baseline": {"lane_id": "base", "metrics": base_metrics},
        "lens_inputs": lens_rows,
        "scenarios": scenarios,
        "best_scenario": best,
        "note": (
            "B-track observation-only ablation. Delta-only evidence; not A-track routing, not live trading trigger, "
            "and not proof of transfer from compression recovery."
        ),
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    print(
        f"BASE hit={base_metrics['price_directional_hit_rate']} n={base_metrics['n_evaluated']} | "
        f"BEST {best['lane_id']} delta={best['delta_hit_rate']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
