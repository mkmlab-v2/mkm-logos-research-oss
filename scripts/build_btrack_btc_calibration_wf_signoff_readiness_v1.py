#!/usr/bin/env python3
"""[HYPO] Calibration shadow sign-off readiness (prod 180d apply evidence)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MARGIN = ROOT / "reports/btrack_btc_margin_walkforward_gate_prod_aligned_v1_latest.json"
DEFAULT_APPLY = ROOT / "reports/btrack_btc_lane2_calibration_apply_recommended_180d_v1_latest.json"
DEFAULT_SIGNOFF = ROOT / "reports/btrack_btc_calibration_wf_human_signoff_latest.json"
DEFAULT_TEMPLATE = ROOT / "reports/btrack_btc_calibration_wf_human_signoff_v1.template.json"
DEFAULT_OUT = ROOT / "reports/btrack_btc_calibration_wf_signoff_readiness_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        o = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return o if isinstance(o, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--margin-json", type=Path, default=DEFAULT_MARGIN)
    ap.add_argument("--apply-json", type=Path, default=DEFAULT_APPLY)
    ap.add_argument("--signoff-json", type=Path, default=DEFAULT_SIGNOFF)
    ap.add_argument("--template-json", type=Path, default=DEFAULT_TEMPLATE)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    margin = _load(args.margin_json)
    apply_doc = _load(args.apply_json)
    signoff = _load(args.signoff_json) or _load(args.template_json)
    global_best = (margin.get("global_holdout") or {}).get("best") or {}
    best_adaptive = margin.get("best_adaptive_family") or {}

    readiness: dict[str, Any] = {
        "schema": "btrack_btc_calibration_wf_signoff_readiness_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "margin_wf_prod_aligned": {
            "best_family": best_adaptive.get("family"),
            "mean_test_delta_oos": best_adaptive.get("mean_test_delta_oos"),
            "positive_test_folds": best_adaptive.get("positive_test_folds"),
            "global_test_delta_oos": global_best.get("test_delta_oos"),
            "selected_params": global_best.get("selected_params"),
        },
        "prod_180d_shadow_apply": {
            "baseline_btc_hit_rate": (apply_doc.get("baseline_btc") or {}).get("price_directional_hit_rate"),
            "shadow_btc_hit_rate": (apply_doc.get("counterfactual_btc") or {}).get("price_directional_hit_rate"),
            "delta_pp": apply_doc.get("delta_hit_rate"),
            "n_changes": apply_doc.get("n_changes"),
            "policy": apply_doc.get("policy"),
        },
        "signoff_status": {
            "approved": bool(signoff.get("approved")),
            "instrument_layer_change_acknowledged": bool(signoff.get("instrument_layer_change_acknowledged")),
            "decision": signoff.get("decision"),
        },
        "checklist": [
            "Confirm operational recommended score stays unchanged.",
            "Calibration shadow is separate from Type-A sign-off (does_not_replace_type_a_signoff).",
            "Review prod 180d apply delta and n_changes before sign-off.",
            "Record: py scripts/record_btrack_btc_calibration_wf_human_signoff_v1.py --acknowledge-btc-calibration-layer-change",
            "combined_all_passed and lens gt beat-bull remain unchanged after approval.",
        ],
        "approve_command": (
            "py scripts/record_btrack_btc_calibration_wf_human_signoff_v1.py "
            "--acknowledge-btc-calibration-layer-change --reviewer commander "
            '--note "calibration shadow prod180d reviewed"'
        ),
        "operator_lines": [],
    }
    readiness["operator_lines"] = [
        "- [BTC-CAL-SIGNOFF] research_shadow_only; oper score NOT promoted.",
        f"- [BTC-CAL-SIGNOFF] prod180d delta_pp={apply_doc.get('delta_hit_rate')} "
        f"n_changes={apply_doc.get('n_changes')}.",
        f"- [BTC-CAL-SIGNOFF] WF global_test_delta={global_best.get('test_delta_oos')} "
        f"adaptive_pos_folds={best_adaptive.get('positive_test_folds')}/{best_adaptive.get('total_folds')}.",
        f"- [BTC-CAL-SIGNOFF] signoff approved={readiness['signoff_status']['approved']} "
        f"decision={readiness['signoff_status']['decision']}.",
    ]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(readiness, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    for line in readiness["operator_lines"]:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
