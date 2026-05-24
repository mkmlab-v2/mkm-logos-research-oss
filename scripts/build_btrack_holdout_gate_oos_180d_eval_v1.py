#!/usr/bin/env python3
"""[HYPO] 180d OOS + train_wrong cohort eval for holdout_ovn_signed_bull gate candidate."""
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

from scripts.btrack_wrong_dir_auxiliary_layer_v1 import apply_auxiliary_per_date_doc
from scripts.btrack_wrong_dir_holdout_core_v1 import holdout_dates_from_cf, wrong_dir_cohort_with_auxiliary
from scripts.run_btrack_wrong_dir_holdout_v1 import (
    DEFAULT_CFG,
    DEFAULT_CF,
    DEFAULT_DUMP_180,
    DEFAULT_PER_180,
    WORK,
    _ensure_per_date,
    _load,
    _pipeline_eval,
)

DEFAULT_OUT = ROOT / "reports/btrack_holdout_gate_oos_180d_v1_latest.json"
MANIFEST = ROOT / "reports/btrack_holdout_gate_candidate_v1_latest.json"
PROD_180 = 0.233333
PROD_30 = 0.366667
ALERT_1 = 0.5


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _candidate_layer(manifest: dict[str, Any]) -> dict[str, Any]:
    layer = manifest.get("candidate_layer") if isinstance(manifest.get("candidate_layer"), dict) else {}
    return {
        "enabled": layer.get("enabled", True),
        "action": layer.get("action", "force_neutral"),
        "apply_when": layer.get("apply_when") or {
            "holdout_only": True,
            "preliminary_bull": True,
            "overnight_negative_or_positive": True,
        },
    }


def _eval_window(
    *,
    per_doc: dict[str, Any],
    layer: dict[str, Any],
    days: int,
    prod_baseline: float,
    label: str,
) -> dict[str, Any]:
    slug = "holdout_ovn_signed_bull"
    adj_doc = apply_auxiliary_per_date_doc(per_doc, layer)
    WORK.mkdir(parents=True, exist_ok=True)
    per_out = WORK / f"per_{slug}_{label}.json"
    per_out.write_text(json.dumps(adj_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ev = _pipeline_eval(per_out, days)
    m = ev.get("metrics") if isinstance(ev.get("metrics"), dict) else {}
    rate = float(m.get("price_directional_hit_rate") or 0)
    return {
        "slug": slug,
        "days": days,
        "metrics": {
            "price_directional_hit_rate": m.get("price_directional_hit_rate"),
            "price_hits": m.get("price_hits"),
            "n_evaluated": m.get("n_evaluated"),
            "n_directional_calls": m.get("n_directional_calls"),
            "n_neutral_predictions": m.get("n_neutral_predictions"),
        },
        "alert_1_pass": rate >= ALERT_1,
        "delta_vs_prod_baseline": round(rate - prod_baseline, 6),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--manifest", type=Path, default=MANIFEST)
    ap.add_argument("--patch-manifest", action="store_true", default=True)
    ap.add_argument("--no-patch-manifest", action="store_false", dest="patch_manifest")
    args = ap.parse_args()

    if not args.manifest.is_file():
        print(f"Missing manifest: {args.manifest}", file=sys.stderr)
        return 2
    manifest = _load(args.manifest)
    layer = _candidate_layer(manifest)
    holdout = holdout_dates_from_cf(DEFAULT_CF)

    if not DEFAULT_DUMP_180.is_file():
        print(f"Missing 180d dump: {DEFAULT_DUMP_180}", file=sys.stderr)
        return 2

    # 180d panel
    if not DEFAULT_PER_180.is_file():
        _ensure_per_date(180, DEFAULT_CFG, DEFAULT_PER_180, force=True)
    per180 = _load(DEFAULT_PER_180)
    dump180 = _load(DEFAULT_DUMP_180)
    row180 = _eval_window(
        per_doc=per180, layer=layer, days=180, prod_baseline=PROD_180, label="180d"
    )
    hwd = wrong_dir_cohort_with_auxiliary(per180, dump180, holdout, layer, holdout_only=True)
    twd = wrong_dir_cohort_with_auxiliary(per180, dump180, holdout, layer, holdout_only=False)
    row180["holdout_wrong_dir"] = hwd
    row180["train_wrong_dir"] = twd

    # 30d confirm (manifest uses same per_date path)
    dump30_path = ROOT / "reports/btrack_wrong_dir_holdout_features_v1_latest.json"
    per30_path = ROOT / "reports/btrack_model_swap_work/per_date_baseline_30d.json"
    row30 = None
    hwd30: dict[str, Any] = {}
    if dump30_path.is_file() and per30_path.is_file():
        per30 = _load(per30_path)
        dump30 = _load(dump30_path)
        row30 = _eval_window(per_doc=per30, layer=layer, days=30, prod_baseline=PROD_30, label="30d")
        hwd30 = wrong_dir_cohort_with_auxiliary(per30, dump30, holdout, layer, holdout_only=True)
        row30["holdout_wrong_dir"] = hwd30

    m180 = row180.get("metrics") or {}

    report = {
        "schema": "btrack_holdout_gate_oos_180d_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "candidate_slug": "holdout_ovn_signed_bull",
        "prod_baselines": {"30d": PROD_30, "180d": PROD_180},
        "eval_180d": row180,
        "eval_30d_confirm": row30,
        "verdict": {
            "alert_1_pass_180d": row180.get("alert_1_pass"),
            "headline_delta_180d": row180.get("delta_vs_prod_baseline"),
            "holdout7_wrong_neutralized": hwd.get("neutralized"),
            "holdout7_wrong_bear_fix": hwd.get("bear_fix"),
            "train_wrong_neutralized_180d": twd.get("neutralized"),
            "train_wrong_bear_fix_180d": twd.get("bear_fix"),
            "auto_promote": False,
            "promotion_note_ko": (
                "holdout7 wrong_dir 전부 중립화 가능; 180d headline·ALERT_1·train_wrong bear_fix 미달 시 승격 불가."
            ),
        },
        "operator_lines": [
            "- [MKM-HOLDOUT-GATE-OOS] research_only; auto_promote=false.",
            f"- [MKM-HOLDOUT-GATE-OOS] 180d headline={float(m180.get('price_directional_hit_rate') or 0):.1%} "
            f"delta={row180.get('delta_vs_prod_baseline'):+.1%} A1={'pass' if row180.get('alert_1_pass') else 'fail'}.",
            f"- [MKM-HOLDOUT-GATE-OOS] holdout7 wrong neutralized={hwd.get('neutralized')}/{hwd.get('n_wrong_dir_days')} "
            f"bear_fix={hwd.get('bear_fix')}.",
            f"- [MKM-HOLDOUT-GATE-OOS] train_wrong 180d neutralized={twd.get('neutralized')}/{twd.get('n_wrong_dir_days')} "
            f"bear_fix={twd.get('bear_fix')}.",
        ],
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")

    if args.patch_manifest:
        manifest["metrics_180d_oos"] = {
            "path": str(args.output),
            "headline": m180.get("price_directional_hit_rate"),
            "delta_vs_prod": row180.get("delta_vs_prod_baseline"),
            "alert_1_pass": row180.get("alert_1_pass"),
            "holdout_wrong_dir": hwd,
            "train_wrong_dir": twd,
        }
        base_ops = [
            ln
            for ln in (manifest.get("operator_lines") or [])
            if isinstance(ln, str) and not ln.startswith("- [MKM-HOLDOUT-GATE-OOS]")
        ]
        manifest["operator_lines"] = base_ops + list(report["operator_lines"])
        args.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"PATCHED: {args.manifest.resolve()}")

    for line in report["operator_lines"]:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
