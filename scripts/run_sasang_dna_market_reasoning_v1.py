#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

AXES = ("TY", "SY", "TE", "SE")
NEWS_FIELD_HINTS = ("news", "headline", "article", "press", "journal", "history")


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe_float(v: Any) -> float:
    try:
        if v is None:
            return 0.0
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _pearson(xs: list[float], ys: list[float]) -> float | None:
    n = len(xs)
    if n < 2:
        return None
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den_x = sum((x - mx) ** 2 for x in xs)
    den_y = sum((y - my) ** 2 for y in ys)
    den = (den_x * den_y) ** 0.5
    if den <= 0:
        return None
    return num / den


def _normalize(v: dict[str, float]) -> dict[str, float]:
    s = sum(v.values())
    if s <= 0:
        return {k: 0.25 for k in AXES}
    return {k: (float(v[k]) / s) for k in AXES}


def _run(cmd: list[str]) -> None:
    r = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if r.returncode != 0:
        raise RuntimeError(r.stderr or r.stdout)


def _top_axis(axis_vec: dict[str, float]) -> str:
    return sorted(axis_vec.items(), key=lambda kv: (-kv[1], AXES.index(kv[0])))[0][0]


def _build_market_axis_row(row: dict[str, str]) -> tuple[dict[str, float], dict[str, float]]:
    fear = _safe_float(row.get("fear_score"))
    greed = _safe_float(row.get("greed_score"))
    panic = _safe_float(row.get("panic_ratio"))
    fomo = _safe_float(row.get("fomo_index"))
    vol = _safe_float(row.get("volatility_score"))
    disp = _safe_float(row.get("dispersion_score"))

    # Heuristic market-psych to Sasang axis mapping (B-track).
    raw = {
        "TY": max(0.0, greed + 0.6 * fomo + 0.2 * (1.0 - panic)),
        "SY": max(0.0, 0.7 * greed + 0.4 * disp + 0.3 * (1.0 - fear)),
        "TE": max(0.0, fear + 0.7 * panic + 0.5 * vol),
        "SE": max(0.0, 0.8 * (1.0 - vol) + 0.6 * (1.0 - panic) + 0.3 * (1.0 - disp)),
    }
    market_axis = _normalize(raw)
    metrics = {
        "fear_score": fear,
        "greed_score": greed,
        "panic_ratio": panic,
        "fomo_index": fomo,
        "volatility_score": vol,
        "dispersion_score": disp,
    }
    return market_axis, metrics


def _build_interpretation_contribution_table(
    latest_axis: dict[str, float],
    latest_market_metrics: dict[str, float] | None,
) -> dict[str, Any]:
    mm = latest_market_metrics or {}
    fear = _safe_float(mm.get("fear_score"))
    greed = _safe_float(mm.get("greed_score"))
    panic = _safe_float(mm.get("panic_ratio"))
    fomo = _safe_float(mm.get("fomo_index"))
    vol = _safe_float(mm.get("volatility_score"))
    disp = _safe_float(mm.get("dispersion_score"))

    # Geumhwagyoyeok: cross-axis exchange drivers
    geum_components = {
        "axis_ty_sy_spread": abs(latest_axis["TY"] - latest_axis["SY"]),
        "axis_te_se_spread": abs(latest_axis["TE"] - latest_axis["SE"]),
        "sentiment_polarity_gap": abs(greed - fear),
        "panic_fomo_gap": abs(panic - fomo),
    }
    geum_total = sum(geum_components.values()) or 1.0
    geum_table = [
        {
            "factor": k,
            "raw_value": v,
            "contribution_ratio": v / geum_total,
        }
        for k, v in geum_components.items()
    ]
    geum_table.sort(key=lambda x: x["contribution_ratio"], reverse=True)

    # Bomyeongjiju: stability/balance support drivers
    bom_components = {
        "axis_balance_spread_inverse": max(0.0, 1.0 - (max(latest_axis.values()) - min(latest_axis.values()))),
        "low_volatility_support": max(0.0, 1.0 - vol),
        "low_panic_support": max(0.0, 1.0 - panic),
        "low_dispersion_support": max(0.0, 1.0 - disp),
    }
    bom_total = sum(bom_components.values()) or 1.0
    bom_table = [
        {
            "factor": k,
            "raw_value": v,
            "contribution_ratio": v / bom_total,
        }
        for k, v in bom_components.items()
    ]
    bom_table.sort(key=lambda x: x["contribution_ratio"], reverse=True)

    return {
        "geumhwagyoyeok_contribution_table": geum_table,
        "bomyeongjiju_contribution_table": bom_table,
    }


def _byungjeung_transition(stress_series: list[float]) -> dict[str, Any]:
    if not stress_series:
        return {"state": "unknown", "stress_index_latest": 0.0, "transition_hint": "insufficient_data"}
    latest = stress_series[-1]
    prev = stress_series[-2] if len(stress_series) >= 2 else latest
    delta = latest - prev
    if latest >= 0.75:
        state = "crisis"
    elif latest >= 0.55:
        state = "stress"
    elif latest >= 0.35:
        state = "watch"
    else:
        state = "calm"
    if delta > 0.08:
        hint = "aggravating"
    elif delta < -0.08:
        hint = "recovering"
    else:
        hint = "stable_transition"
    return {
        "state": state,
        "stress_index_latest": latest,
        "stress_delta": delta,
        "transition_hint": hint,
    }


def _stress_to_state(stress: float) -> str:
    if stress >= 0.75:
        return "crisis"
    if stress >= 0.55:
        return "stress"
    if stress >= 0.35:
        return "watch"
    return "calm"


def _build_transition_model(stress_series: list[float]) -> dict[str, Any]:
    states = ["calm", "watch", "stress", "crisis"]
    counts = {s: {t: 0 for t in states} for s in states}
    seq = [_stress_to_state(s) for s in stress_series]
    for i in range(len(seq) - 1):
        a = seq[i]
        b = seq[i + 1]
        counts[a][b] += 1
    matrix: dict[str, dict[str, float]] = {}
    for a in states:
        total = sum(counts[a].values())
        if total <= 0:
            matrix[a] = {t: 0.0 for t in states}
        else:
            matrix[a] = {t: counts[a][t] / total for t in states}
    latest_state = seq[-1] if seq else "unknown"
    next_probs = matrix.get(latest_state, {t: 0.0 for t in states})
    return {
        "states": states,
        "state_sequence": seq,
        "transition_counts": counts,
        "transition_matrix": matrix,
        "latest_state": latest_state,
        "next_state_probabilities": next_probs,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Sasang reasoning lane (DNA + market psychology only, no news).")
    root = Path(__file__).resolve().parents[1]
    ap.add_argument("--genotype-csv", type=Path, default=root / "tmp" / "bio_genotype_long_v1.csv")
    ap.add_argument("--cohort-csv", type=Path, default=root / "tmp" / "bio_real_cohort_merged_with_sidecar_v1.csv")
    ap.add_argument("--market-psych-csv", type=Path, required=True)
    ap.add_argument("--axis-weights-json", type=Path, default=root / "tmp" / "agct_sasang_axis_weights_active_btrack_v1.json")
    ap.add_argument("--dna-weight", type=float, default=0.6)
    ap.add_argument("--market-weight", type=float, default=0.4)
    ap.add_argument(
        "--output-json",
        type=Path,
        default=root / "reports" / "sasang_dna_market_reasoning_v1_latest.json",
    )
    ns = ap.parse_args()

    projection_script = root / "scripts" / "run_agct_sasang_composition_projection_v1.py"
    proj_out = root / "reports" / "agct_sasang_composition_projection_for_reasoning_v1.json"
    _run(
        [
            sys.executable,
            str(projection_script),
            "--genotype-csv",
            str(ns.genotype_csv),
            "--cohort-csv",
            str(ns.cohort_csv),
            "--axis-weights-json",
            str(ns.axis_weights_json),
            "--output-json",
            str(proj_out),
        ]
    )
    proj = json.loads(proj_out.read_text(encoding="utf-8"))
    dataset_schema = root / "docs" / "final" / "artifacts" / "schemas" / "sasang_dna_market_training_dataset_v1.schema.json"
    formula_schema = root / "docs" / "final" / "artifacts" / "schemas" / "sasang_4d_gematria_formula_v1.schema.json"
    dna_axis = {
        a: _safe_float((proj.get("summary", {}).get("axis_summary", {}).get(a, {}) or {}).get("mean_projection"))
        for a in AXES
    }
    dna_axis = _normalize(dna_axis)

    with ns.market_psych_csv.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fields = [str(x or "") for x in (reader.fieldnames or [])]
        fields_lower = [x.lower() for x in fields]
        if any(any(h in fld for h in NEWS_FIELD_HINTS) for fld in fields_lower):
            raise SystemExit("market-psych CSV contains forbidden news/history field hints.")
        rows = list(reader)

    timeline = []
    stress_series: list[float] = []
    align_x: list[float] = []
    align_y: list[float] = []
    for r in rows:
        market_axis, raw_metrics = _build_market_axis_row(r)
        fused_axis = _normalize(
            {
                a: ns.dna_weight * dna_axis[a] + ns.market_weight * market_axis[a]
                for a in AXES
            }
        )
        top = _top_axis(fused_axis)
        stress = 0.6 * fused_axis["TE"] + 0.4 * fused_axis["SE"]
        stress_series.append(stress)
        align_x.append(fused_axis["TY"] + fused_axis["SY"])
        align_y.append(fused_axis["TE"] + fused_axis["SE"])
        timeline.append(
            {
                "timestamp_utc": r.get("timestamp_utc"),
                "market_axis": market_axis,
                "fused_axis": fused_axis,
                "top_axis": top,
                "stress_index": stress,
                "market_metrics": raw_metrics,
            }
        )

    byung = _byungjeung_transition(stress_series)
    byung_model = _build_transition_model(stress_series)
    latest_axis = timeline[-1]["fused_axis"] if timeline else {a: 0.25 for a in AXES}
    latest_market_metrics = timeline[-1]["market_metrics"] if timeline else None
    geumhwagyoyeok_exchange = abs((latest_axis["TY"] - latest_axis["SY"]) - (latest_axis["TE"] - latest_axis["SE"]))
    bomyeongjiju_balance = 1.0 - max(latest_axis.values()) + min(latest_axis.values())
    contribution_tables = _build_interpretation_contribution_table(latest_axis, latest_market_metrics)

    payload = {
        "schema": "sasang_dna_market_reasoning_v1",
        "generated_at_utc": _utc_now(),
        "track": "B_TRACK",
        "governance": {
            "news_history_lane_excluded": True,
            "research_only": True,
            "non_gating": True,
        },
        "inputs": {
            "genotype_csv": str(ns.genotype_csv.resolve()),
            "cohort_csv": str(ns.cohort_csv.resolve()) if ns.cohort_csv.is_file() else None,
            "market_psych_csv": str(ns.market_psych_csv.resolve()),
            "axis_weights_json": str(ns.axis_weights_json.resolve()) if ns.axis_weights_json.is_file() else None,
            "dna_weight": ns.dna_weight,
            "market_weight": ns.market_weight,
        },
        "relation_schema": {
            "four_types": list(AXES),
            "fusion_rule": "fused_axis = normalize(dna_weight*dna_axis + market_weight*market_axis)",
            "forbidden_inputs": ["news", "history"],
        },
        "contracts": {
            "training_dataset_schema": str(dataset_schema.resolve()) if dataset_schema.is_file() else None,
            "gematria_formula_schema": str(formula_schema.resolve()) if formula_schema.is_file() else None,
        },
        "summary": {
            "samples_used_for_dna_projection": _safe_float(proj.get("summary", {}).get("samples_used")),
            "market_rows_used": len(timeline),
            "dna_axis_mean": dna_axis,
            "latest_fused_axis": latest_axis,
            "latest_top_axis": _top_axis(latest_axis),
            "alignment_corr_ty_sy_vs_te_se": _pearson(align_x, align_y),
        },
        "byungjeungyakri_transition": byung,
        "byungjeungyakri_transition_model": byung_model,
        "interpretation_engine": {
            "geumhwagyoyeok_exchange_index": geumhwagyoyeok_exchange,
            "bomyeongjiju_balance_index": bomyeongjiju_balance,
            "contribution_decomposition": contribution_tables,
            "interpretation": {
                "geumhwagyoyeok": "Lower is more synchronized cross-axis exchange.",
                "bomyeongjiju": "Higher indicates stronger baseline balance/stability support.",
            },
        },
        "timeline_preview": timeline[:20],
        "notes": [
            "Sasang lane excludes news/history and is separate from Logos lane.",
            "This artifact is for B-track quantitative diagnostics only.",
        ],
    }
    ns.output_json.parent.mkdir(parents=True, exist_ok=True)
    ns.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {ns.output_json.resolve()} rows={len(timeline)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
