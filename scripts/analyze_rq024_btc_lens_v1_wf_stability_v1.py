#!/usr/bin/env python3
"""[HYPO] RQ-024 v1 blocked-WF stability: nf sensitivity + per-fold weight/accuracy deltas."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_WF = ROOT / "reports/rq024_btc_lens_feature_v0_wf_ablation_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/rq024_btc_lens_v1_wf_stability_v1_latest.json"
SCHEMA = "rq024_btc_lens_v1_wf_stability_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _weight_key(w: dict[str, Any] | None) -> str:
    if not w:
        return "unknown"
    return (
        f"ovn={w.get('w_overnight')}|pr={w.get('w_prior_range_centered')}|"
        f"dd={w.get('w_drawdown_20d')}|ldr={w.get('w_last_daily_return')}|"
        f"vol={w.get('w_realized_vol_5d')}"
    )


def _fold_rows(variant: dict[str, Any]) -> list[dict[str, Any]]:
    detail = variant.get("detail") or {}
    folds = (detail.get("rq024_causal_lens_v1") or {}).get("folds") or []
    rows: list[dict[str, Any]] = []
    for f in folds:
        tb = f.get("test_blind") or {}
        rows.append(
            {
                "fold_index": f.get("fold_index"),
                "test_accuracy": tb.get("accuracy"),
                "beats_052": tb.get("beats_ceiling_052"),
                "causal_weights_v1": f.get("causal_weights_v1"),
                "weight_key": _weight_key(f.get("causal_weights_v1")),
            }
        )
    return rows


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--wf-json", type=Path, default=DEFAULT_WF)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    wf_path = args.wf_json if args.wf_json.is_absolute() else ROOT / args.wf_json
    wf = _load(wf_path)
    variants = wf.get("variants") or []
    if not variants:
        raise SystemExit(f"no variants in {wf_path}")

    nf_rows: list[dict[str, Any]] = []
    weak_nf: list[dict[str, Any]] = []
    strong_nf: list[dict[str, Any]] = []
    all_weight_keys: Counter[str] = Counter()

    for v in variants:
        nf = int(v.get("n_folds") or 0)
        b_mean = float((v.get("baseline_aggregate") or {}).get("mean_test_accuracy") or 0)
        v0_mean = float((v.get("v0_aggregate") or {}).get("mean_test_accuracy") or 0)
        v1_mean = float((v.get("v1_aggregate") or {}).get("mean_test_accuracy") or 0)
        v1_frac = float((v.get("v1_aggregate") or {}).get("fraction_test_beats_ceiling_052") or 0)
        fold_detail = _fold_rows(v)
        for fd in fold_detail:
            all_weight_keys[fd["weight_key"]] += 1

        row = {
            "n_folds": nf,
            "slug": v.get("slug"),
            "baseline_mean": b_mean,
            "v0_mean": v0_mean,
            "v1_mean": v1_mean,
            "delta_v1_minus_v0": round(v1_mean - v0_mean, 6),
            "delta_v1_minus_baseline": round(v1_mean - b_mean, 6),
            "v1_fraction_beats_052": v1_frac,
            "v1_beats_052_mean": v1_mean > 0.52,
            "folds_v1": fold_detail,
        }
        nf_rows.append(row)
        if v1_mean < 0.52 or v1_frac < 0.5:
            weak_nf.append(row)
        if v1_mean >= 0.52 and v1_frac >= 0.5:
            strong_nf.append(row)

    best = max(nf_rows, key=lambda r: r["v1_mean"], default=None)
    weight_mode = all_weight_keys.most_common(3)

    hypotheses: list[str] = []
    if weak_nf:
        weak_ids = [r["n_folds"] for r in weak_nf]
        hypotheses.append(
            f"nf{weak_ids}: v1 mean or fold-fraction below 0.52 — fold count changes train window size; "
            "5-weight grid may overfit smaller train blocks or underfit when too many folds shrink test."
        )
    if best and best["n_folds"] == 5:
        hypotheses.append(
            "nf5 peak (mean 0.535): middle fold count balances train size for 243-combo v1 grid vs generalization."
        )
    if weight_mode:
        hypotheses.append(f"Most frequent v1 weight tuples across folds: {weight_mode[:2]}")

    out: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "rq_id": "RQ-024",
        "inputs": {"wf_json": str(wf_path.relative_to(ROOT)).replace("\\", "/")},
        "nf_sensitivity": nf_rows,
        "strong_nf_configs": [{"n_folds": r["n_folds"], "v1_mean": r["v1_mean"]} for r in strong_nf],
        "weak_nf_configs": [
            {
                "n_folds": r["n_folds"],
                "v1_mean": r["v1_mean"],
                "v1_fraction_beats_052": r["v1_fraction_beats_052"],
                "delta_v1_minus_v0": r["delta_v1_minus_v0"],
            }
            for r in weak_nf
        ],
        "best_v1_nf": best.get("n_folds") if best else None,
        "weight_mode_top3": [{"key": k, "count": c} for k, c in weight_mode],
        "stability_readout": {
            "v1_nf_dependent": len(strong_nf) > 0 and len(weak_nf) > 0,
            "only_nf5_passes_both_mean_and_fraction": bool(
                strong_nf and all(r["n_folds"] == 5 for r in strong_nf) and any(r["n_folds"] != 5 for r in weak_nf)
            ),
        },
        "operator_hypotheses": hypotheses,
    }

    out_path = args.output if args.output.is_absolute() else ROOT / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out_path.resolve()}")
    for r in nf_rows:
        print(
            f"nf{r['n_folds']}: v1_mean={r['v1_mean']} delta_v1_v0={r['delta_v1_minus_v0']} "
            f"frac_052={r['v1_fraction_beats_052']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
