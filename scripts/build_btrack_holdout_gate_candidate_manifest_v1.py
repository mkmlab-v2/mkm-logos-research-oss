#!/usr/bin/env python3
"""[HYPO] Register holdout_ovn_signed_bull B-track gate candidate (research; no prod promote)."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.btrack_wrong_dir_auxiliary_layer_v1 import (
    apply_auxiliary_per_date_doc,
    apply_auxiliary_to_row,
)
from scripts.btrack_wrong_dir_holdout_core_v1 import enrich_per_date_doc_btc, holdout_dates_from_cf

DEFAULT_OUT = ROOT / "reports/btrack_holdout_gate_candidate_v1_latest.json"
PROBE = ROOT / "reports/btrack_holdout7_uncovered_four_probe_v1_latest.json"
GATE_PACK = ROOT / "reports/btrack_holdout7_gate_research_pack_v1_latest.json"
HOLDOUT30D_SWEEP = ROOT / "reports/btrack_holdout30d_headline_sweep_v1_latest.json"
HYBRID_MATRIX = ROOT / "reports/btrack_frozen30d_hybrid_rule_matrix_v1_latest.json"
HYBRID_SHADOW = ROOT / "reports/btrack_bbs_ms_hybrid_shadow_lane_v1_latest.json"
PANEL = ROOT / "reports/btrack_holdout7_gemini_vs_prod_panel_v1_latest.json"
CF = ROOT / "reports/btrack_wrong_dir_counterfactual_matrix_v1_latest.json"
DUMP = ROOT / "reports/btrack_wrong_dir_holdout_features_v1_latest.json"
PER_DATE = ROOT / "reports/btrack_ensemble_per_date_directions_180d_v1_latest.json"
WORK = ROOT / "reports/btrack_holdout_gate_candidate_work"
BTC = ROOT / "research/market_data/btc_daily_external_yf.csv"
KOSPI = ROOT / "research/market_data/kospi_daily_external_yf.csv"

CANDIDATE_LAYER: dict[str, Any] = {
    "slug": "holdout_ovn_signed_bull",
    "enabled": True,
    "action": "force_neutral",
    "apply_when": {
        "holdout_only": True,
        "preliminary_bull": True,
        "overnight_negative_or_positive": True,
    },
    "rationale_ko": (
        "holdout7 wrong_dir 7/7: OVN 음수(3일)+양수(4일) 베어 트랩; 30d headline unchanged vs prod; ALERT_1 fail."
    ),
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _holdout30d_sweep_summary(sweep: dict[str, Any]) -> dict[str, Any]:
    hybrid = sweep.get("hybrid_shadow_reference") if isinstance(sweep.get("hybrid_shadow_reference"), dict) else {}
    oracle = sweep.get("oracle_bear_fix_headline") if isinstance(sweep.get("oracle_bear_fix_headline"), dict) else {}
    prod_h = float(sweep.get("prod_rebuild_on_anchor_headline") or 0)
    stack_delta = sweep.get("stack_holdout_headline_delta")
    hybrid_h = hybrid.get("frozen30d_rate")
    return {
        "pointer": str(HOLDOUT30D_SWEEP.relative_to(ROOT)).replace("\\", "/"),
        "eval_panel": sweep.get("eval_panel"),
        "anchor_n_dates": len(sweep.get("anchor_dates") or []),
        "prod_rebuild_headline": prod_h,
        "stack_headline_delta": stack_delta,
        "oracle_upper_bound_headline": float(oracle.get("price_directional_hit_rate") or 0),
        "hybrid_bbs_ms_frozen30d": float(hybrid_h) if hybrid_h is not None else None,
        "hybrid_bbs_ms_holdout7": hybrid.get("holdout7_rate"),
        "recommendation_ko": sweep.get("recommendation_ko"),
        "structural_note_ko": sweep.get("structural_note_ko"),
        "operator_lines": list(sweep.get("operator_lines") or []),
    }


def _hybrid_shadow_summary(shadow: dict[str, Any], matrix: dict[str, Any]) -> dict[str, Any] | None:
    if not shadow and not matrix:
        return None
    lane_key = "bbs_ms_agree_or_ms_else"
    mx = ((matrix or {}).get("matrix") or {}).get(lane_key) or {}
    metrics = (shadow or {}).get("metrics") if isinstance((shadow or {}).get("metrics"), dict) else {}
    full = mx.get("full_30d") or {}
    h7 = mx.get("holdout7") or {}
    frozen_h = float(metrics.get("frozen_30d_all_rows") or full.get("rate") or 0)
    holdout_h = float(metrics.get("holdout7") or h7.get("rate") or 0)
    baseline = float(metrics.get("frozen_kpi_a_baseline") or 0.433333)
    return {
        "lane_id": (shadow or {}).get("lane_id") or "bbs_ms_hybrid_frozen30d_v1",
        "rule_slug": lane_key,
        "pointer_shadow": str(HYBRID_SHADOW.relative_to(ROOT)).replace("\\", "/")
        if HYBRID_SHADOW.is_file()
        else None,
        "pointer_matrix": str(HYBRID_MATRIX.relative_to(ROOT)).replace("\\", "/")
        if HYBRID_MATRIX.is_file()
        else None,
        "frozen30d_anchor_headline": frozen_h,
        "holdout7_headline": holdout_h,
        "frozen_kpi_a_baseline": baseline,
        "delta_pp_vs_kpi_a": round((frozen_h - baseline) * 100, 4) if frozen_h else None,
        "alert_1_pass_frozen30d": frozen_h >= 0.5,
        "operator_recommendation": (shadow or {}).get("operator_recommendation") or "shadow_only_not_headline",
        "do_not": list((shadow or {}).get("do_not") or []),
    }


def _hybrid_shadow_operator_lines(summary: dict[str, Any]) -> list[str]:
    frozen_h = float(summary.get("frozen30d_anchor_headline") or 0)
    holdout_h = float(summary.get("holdout7_headline") or 0)
    return [
        "- [MKM-HOLDOUT-GATE] hybrid bbs_ms shadow lane; research_only; auto_promote=false.",
        f"- [MKM-HOLDOUT-GATE] hybrid frozen30d={frozen_h:.1%} holdout7={holdout_h:.1%} "
        f"delta_pp={summary.get('delta_pp_vs_kpi_a')} vs KPI-A baseline.",
        f"- [MKM-HOLDOUT-GATE] headline uplift path=hybrid shadow (not holdout aux stack); "
        f"pointer={summary.get('pointer_matrix')}.",
    ]


def _holdout30d_operator_lines(summary: dict[str, Any]) -> list[str]:
    prod_h = float(summary.get("prod_rebuild_headline") or 0)
    stack_delta = summary.get("stack_headline_delta")
    oracle_h = float(summary.get("oracle_upper_bound_headline") or 0)
    hybrid_h = summary.get("hybrid_bbs_ms_frozen30d")
    hybrid_txt = f"{float(hybrid_h):.1%}" if hybrid_h is not None else "n/a"
    return [
        "- [MKM-HOLDOUT-GATE] frozen30d anchor sweep wired; research_only; auto_promote=false.",
        f"- [MKM-HOLDOUT-GATE] frozen30d prod={prod_h:.1%} stack_delta={stack_delta} "
        f"oracle={oracle_h:.1%} stack_headline_lift=0.",
        f"- [MKM-HOLDOUT-GATE] frozen30d hybrid bbs_ms={hybrid_txt} (별도 레인·headline uplift).",
        f"- [MKM-HOLDOUT-GATE] pointer={summary.get('pointer')}.",
    ]


def _pipeline_eval(per_date: Path, tag: str) -> dict[str, Any]:
    WORK.mkdir(parents=True, exist_ok=True)
    score = WORK / f"score_{tag}.json"
    ev_out = WORK / f"eval_{tag}.json"
    for cmd in [
        [
            "scripts/build_btrack_prophecy_score_from_ohlcv.py",
            "--recent-trading-days",
            "30",
            "--force-dual-leg-panel",
            "--btc-csv",
            str(BTC.relative_to(ROOT)),
            "--kospi-csv",
            str(KOSPI.relative_to(ROOT)),
            "--per-date-direction-json",
            str(per_date.relative_to(ROOT)),
            "--output",
            str(score.relative_to(ROOT)),
        ],
        [
            "scripts/eval_prophecy_hit_rate_v1.py",
            "--run-mode",
            "price",
            "--score-json",
            str(score.relative_to(ROOT)),
            "--output",
            str(ev_out.relative_to(ROOT)),
        ],
    ]:
        p = subprocess.run([sys.executable, *cmd], cwd=ROOT, capture_output=True, text=True)
        if p.returncode != 0:
            return {"status": "failed", "stderr": (p.stderr or "")[-1200:]}
    ev = _load(ev_out)
    m = ev.get("metrics") if isinstance(ev.get("metrics"), dict) else {}
    leg = (m.get("legs") or {}).get("btc") if isinstance(m.get("legs"), dict) else {}
    if not isinstance(leg, dict):
        leg = m
    h = float(leg.get("price_directional_hit_rate") or m.get("price_directional_hit_rate") or 0)
    return {
        "status": "ok",
        "price_directional_hit_rate": h,
        "alert_1_pass": h >= 0.5,
        "eval": str(ev_out),
    }


def _holdout7_neutralized(
    per_doc: dict[str, Any], holdout: list[str], dump: dict[str, Any]
) -> dict[str, Any]:
    holdout_set = set(holdout)
    enriched = enrich_per_date_doc_btc(per_doc, holdout)
    dump_by = {str(r.get("eval_date"))[:10]: r for r in dump.get("rows") or [] if isinstance(r, dict)}
    neutralized: list[str] = []
    for r in enriched.get("rows") or []:
        if not isinstance(r, dict) or str(r.get("instrument") or "").lower() != "btc":
            continue
        ed = str(r.get("eval_date") or "")[:10]
        if ed not in holdout_set:
            continue
        base = dump_by.get(ed) or {}
        pred = str(r.get("predicted_direction") or "").lower()
        act = str(base.get("actual_direction") or r.get("actual_direction") or "").lower()
        if pred in ("bull", "bear") and act in ("bull", "bear") and pred != act:
            row = dict(r)
            row["is_holdout_7"] = True
            row["actual_direction"] = act
            adj = apply_auxiliary_to_row(row, CANDIDATE_LAYER)
            if adj.get("auxiliary_applied") and str(adj.get("adjusted_direction") or "").lower() == "neutral":
                neutralized.append(ed)
    return {
        "n_holdout7_wrong_neutralized": len(neutralized),
        "neutralized_dates": sorted(neutralized),
        "covers_all_holdout7_wrong": len(neutralized) == 7,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--skip-probe-refresh", action="store_true")
    ap.add_argument("--skip-30d-sweep-refresh", action="store_true")
    ap.add_argument("--skip-eval", action="store_true")
    args = ap.parse_args()

    if not args.skip_probe_refresh:
        p = subprocess.run(
            [sys.executable, "scripts/build_btrack_holdout7_uncovered_four_probe_v1.py", "--skip-eval"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        if p.returncode != 0:
            print(p.stderr or p.stdout, file=sys.stderr)
            return 1

    if not args.skip_30d_sweep_refresh:
        p = subprocess.run(
            [sys.executable, "scripts/build_btrack_holdout30d_headline_sweep_v1.py"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        if p.returncode != 0:
            print(p.stderr or p.stdout, file=sys.stderr)
            return 1

    if not PER_DATE.is_file():
        print(f"Missing {PER_DATE}", file=sys.stderr)
        return 2

    holdout = holdout_dates_from_cf(CF)
    per_base = _load(PER_DATE)
    dump = _load(DUMP) if DUMP.is_file() else {"rows": []}
    patched = apply_auxiliary_per_date_doc(per_base, CANDIDATE_LAYER)
    out_per = WORK / "per_date_holdout_ovn_signed_bull.json"
    WORK.mkdir(parents=True, exist_ok=True)
    out_per.write_text(json.dumps(patched, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    h7 = _holdout7_neutralized(per_base, holdout, dump)
    eval_30d = None if args.skip_eval else _pipeline_eval(out_per, "holdout_ovn_signed_bull")

    probe = _load(PROBE) if PROBE.is_file() else {}
    pack = _load(GATE_PACK) if GATE_PACK.is_file() else {}
    tradeoff = probe.get("tradeoff_pr_high_vs_signed_bull") or {}
    stack = tradeoff.get("stack_signed_bull_plus_neutral_miss") or {}

    prod_h = 0.366667
    cand_h = float((eval_30d or {}).get("price_directional_hit_rate") or prod_h) if eval_30d else prod_h

    sweep_doc = _load(HOLDOUT30D_SWEEP) if HOLDOUT30D_SWEEP.is_file() else {}
    h30_summary = _holdout30d_sweep_summary(sweep_doc) if sweep_doc else None
    hybrid_shadow_doc = _load(HYBRID_SHADOW) if HYBRID_SHADOW.is_file() else {}
    hybrid_matrix_doc = _load(HYBRID_MATRIX) if HYBRID_MATRIX.is_file() else {}
    hybrid_summary = _hybrid_shadow_summary(hybrid_shadow_doc, hybrid_matrix_doc)

    operator_lines = [
        "- [MKM-HOLDOUT-GATE] candidate=holdout_ovn_signed_bull; research_only; auto_promote=false.",
        f"- [MKM-HOLDOUT-GATE] holdout7 wrong_dir neutralized {h7.get('n_holdout7_wrong_neutralized')}/7.",
        f"- [MKM-HOLDOUT-GATE] research_stack signed_bull+neutral_miss "
        f"{stack.get('n_covered', '?')}/7 covers_all={stack.get('covers_all_bear_trap')}.",
        f"- [MKM-HOLDOUT-GATE] rolling30d headline prod={prod_h:.1%} candidate={cand_h:.1%} "
        f"A1={'pass' if (eval_30d or {}).get('alert_1_pass') else 'fail'}.",
        "- [MKM-HOLDOUT-GATE] model_swap PoC closed; advisory unchanged; no Track A.",
    ]
    if h30_summary:
        operator_lines.extend(_holdout30d_operator_lines(h30_summary))
    if hybrid_summary:
        operator_lines.extend(_hybrid_shadow_operator_lines(hybrid_summary))

    report = {
        "schema": "btrack_holdout_gate_candidate_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "candidate_layer": CANDIDATE_LAYER,
        "deployment": {
            "target": "b_track_auxiliary_post_ensemble",
            "ensemble_json_untouched": True,
            "track_a_live": False,
            "auto_promote": False,
            "verdict": "research_candidate_holdout_only",
        },
        "evidence": {
            "holdout7_panel": str(PANEL) if PANEL.is_file() else None,
            "gate_research_pack": str(GATE_PACK) if GATE_PACK.is_file() else None,
            "uncovered_four_probe": str(PROBE) if PROBE.is_file() else None,
            "holdout30d_headline_sweep": str(HOLDOUT30D_SWEEP) if HOLDOUT30D_SWEEP.is_file() else None,
            "hybrid_shadow_lane": str(HYBRID_SHADOW) if HYBRID_SHADOW.is_file() else None,
            "hybrid_rule_matrix": str(HYBRID_MATRIX) if HYBRID_MATRIX.is_file() else None,
            "model_swap_closed": True,
            "gemini_holdout7_wrong_dir": "7/7 same as prod (panel)",
        },
        "holdout7": h7,
        "research_composite_stack": {
            "slug_pair": ["holdout_ovn_signed_bull", "holdout_prelim_bull_pred_neutral_miss"],
            "n_bear_trap_covered": stack.get("n_covered"),
            "covers_all_bear_trap": stack.get("covers_all_bear_trap"),
            "dates": stack.get("dates") or [],
            "note_ko": "단일 규칙 후보는 signed_bull; 04-02는 neutral_miss advisory 병행(연구 composite).",
        },
        "metrics_30d": {
            "panel": "rolling_recent_30_trading_days",
            "prod_baseline_headline": prod_h,
            "with_candidate_headline": cand_h,
            "delta_headline": round(cand_h - prod_h, 6),
            "alert_1_pass": bool((eval_30d or {}).get("alert_1_pass")),
            "eval_path": (eval_30d or {}).get("eval"),
        },
        "holdout30d_anchor_sweep": h30_summary,
        "hybrid_shadow_lane": hybrid_summary,
        "probe_best_slug": (probe.get("best_probe") or {}).get("slug"),
        "operator_lines": operator_lines,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    for line in report["operator_lines"]:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
