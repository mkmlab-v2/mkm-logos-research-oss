#!/usr/bin/env python3
"""[HYPO] Lane2 BTC oper vs shadow reconcile on prod-aligned 180d (no oper promotion)."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/btrack_btc_lane2_oper_shadow_reconcile_v1_latest.json"

OPER_180 = ROOT / "reports/btrack_btc_lane2_typea_apply_recommended_180d_v1_latest.json"
CAL_APPLY = ROOT / "reports/btrack_btc_lane2_calibration_apply_recommended_180d_v1_latest.json"
CAL_SIGNOFF = ROOT / "reports/btrack_btc_calibration_wf_human_signoff_latest.json"
CAL_READINESS = ROOT / "reports/btrack_btc_calibration_wf_signoff_readiness_v1_latest.json"
OPER_30 = ROOT / "reports/btrack_btc_typea_guard_apply_summary_v1_latest.json"
MARGIN_REBUILD = ROOT / "reports/btrack_btc_margin_walkforward_gate_v1_latest.json"
MARGIN_PROD = ROOT / "reports/btrack_btc_margin_walkforward_gate_prod_aligned_v1_latest.json"
SIGNOFF = ROOT / "reports/btrack_btc_margin_wf_human_signoff_latest.json"
SHADOW_EVAL = ROOT / "reports/btrack_btc_lane2_shadow_hit_eval_180d_v1_latest.json"
RECOMMENDED_SCORE = ROOT / "reports/btrack_prophecy_score_recommended_eval_chain_v1_latest.json"


def _utc() -> str:
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
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    a180 = _load(OPER_180)
    cal180 = _load(CAL_APPLY)
    a30 = _load(OPER_30)
    mr = _load(MARGIN_REBUILD)
    mp = _load(MARGIN_PROD)
    signoff = _load(SIGNOFF)
    cal_signoff = _load(CAL_SIGNOFF)
    shadow_eval = _load(SHADOW_EVAL)

    ledger = (
        "BTC Lane2: Type-A shadow on prod 180d +4.4pp (n_changes=16); oper 30d headline n_changes=0; "
        "lens gt 0/5 blocks combined; no oper/Track A promotion."
    )

    report: dict[str, Any] = {
        "schema": "btrack_btc_lane2_oper_shadow_reconcile_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "track_a_auto_promote": False,
        "send_gate": "HOLD",
        "lane_status": "SHADOW_DOCUMENTED",
        "signoff": {
            "approved": signoff.get("approved"),
            "decision": signoff.get("decision"),
            "scope_research_shadow_only": (signoff.get("scope") or {}).get("research_shadow_only"),
        },
        "operational_score_path": str(RECOMMENDED_SCORE.relative_to(ROOT)).replace("\\", "/"),
        "operational_score_unchanged": True,
        "prod_aligned_180d": {
            "baseline_btc_hit_rate": (a180.get("baseline_btc") or {}).get("price_directional_hit_rate"),
            "shadow_typea_btc_hit_rate": (a180.get("counterfactual_btc") or {}).get("price_directional_hit_rate"),
            "delta_pp": a180.get("delta_hit_rate"),
            "n_changes": a180.get("n_changes"),
            "artifact_apply": str(OPER_180.relative_to(ROOT)).replace("\\", "/"),
            "shadow_eval_artifact": str(SHADOW_EVAL.relative_to(ROOT)).replace("\\", "/"),
            "shadow_eval_hit_rate": (shadow_eval.get("metrics") or {}).get("price_directional_hit_rate"),
        },
        "oper_headline_30d_panel": {
            "n_changes": a30.get("n_changes"),
            "delta_hit_rate": a30.get("delta_hit_rate"),
            "note": "Daily oper headline uses 30d KOSPI shock-cutoff panel; Type-A guard inactive (n_changes=0).",
            "artifact": str(OPER_30.relative_to(ROOT)).replace("\\", "/"),
        },
        "margin_walkforward": {
            "rebuild_path_global_test_delta": ((mr.get("global_holdout") or {}).get("best") or {}).get(
                "test_delta_oos"
            ),
            "prod_aligned_best_family": (mp.get("best_adaptive_family") or {}).get("family"),
            "prod_aligned_mean_test_delta_oos": (mp.get("best_adaptive_family") or {}).get("mean_test_delta_oos"),
            "prod_aligned_global_test_delta": ((mp.get("global_holdout") or {}).get("best") or {}).get(
                "test_delta_oos"
            ),
            "rebuild_artifact": str(MARGIN_REBUILD.relative_to(ROOT)).replace("\\", "/"),
            "prod_aligned_artifact": str(MARGIN_PROD.relative_to(ROOT)).replace("\\", "/"),
            "calibration_not_signed_off": not bool(cal_signoff.get("approved")),
        },
        "calibration_shadow_180d": {
            "baseline_btc_hit_rate": (cal180.get("baseline_btc") or {}).get("price_directional_hit_rate"),
            "shadow_btc_hit_rate": (cal180.get("counterfactual_btc") or {}).get("price_directional_hit_rate"),
            "delta_pp": cal180.get("delta_hit_rate"),
            "n_changes": cal180.get("n_changes"),
            "wf_global_test_delta_note": "WF OOS delta != full 180d apply delta; review both",
            "signoff_decision": cal_signoff.get("decision", "PENDING"),
            "signoff_readiness": str(CAL_READINESS.relative_to(ROOT)).replace("\\", "/"),
            "apply_artifact": str(CAL_APPLY.relative_to(ROOT)).replace("\\", "/"),
        },
        "combined_blocker": "lens_wf_fraction_folds_beat_always_bull_gt",
        "ledger_line": ledger,
        "operator_lines": [
            "- [BTC-LANE2] research_only; oper recommended score NOT overwritten.",
            f"- [BTC-LANE2] prod 180d oper_btc={(a180.get('baseline_btc') or {}).get('price_directional_hit_rate')} "
            f"shadow_typea={(a180.get('counterfactual_btc') or {}).get('price_directional_hit_rate')} "
            f"delta_pp={a180.get('delta_hit_rate')} n_changes={a180.get('n_changes')}.",
            f"- [BTC-LANE2] oper 30d headline n_changes={a30.get('n_changes')} (panel mismatch).",
            "- [BTC-LANE2] combined_all_passed remains false; SEND_GATE HOLD.",
            f"- [BTC-LANE2] calibration shadow prod180d delta_pp={cal180.get('delta_hit_rate')} "
            f"n_changes={cal180.get('n_changes')} signoff={cal_signoff.get('decision', 'PENDING')}.",
        ],
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    for line in report["operator_lines"]:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
