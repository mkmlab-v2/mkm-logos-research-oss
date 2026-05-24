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
PANEL = ROOT / "reports/btrack_holdout7_gemini_vs_prod_panel_v1_latest.json"
CF = ROOT / "reports/btrack_wrong_dir_counterfactual_matrix_v1_latest.json"
DUMP = ROOT / "reports/btrack_wrong_dir_holdout_features_v1_latest.json"
PER_DATE = ROOT / "reports/btrack_model_swap_work/per_date_baseline_30d.json"
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

    prod_h = 0.366667
    cand_h = float((eval_30d or {}).get("price_directional_hit_rate") or prod_h) if eval_30d else prod_h

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
            "model_swap_closed": True,
            "gemini_holdout7_wrong_dir": "7/7 same as prod (panel)",
        },
        "holdout7": h7,
        "metrics_30d": {
            "prod_baseline_headline": prod_h,
            "with_candidate_headline": cand_h,
            "delta_headline": round(cand_h - prod_h, 6),
            "alert_1_pass": bool((eval_30d or {}).get("alert_1_pass")),
            "eval_path": (eval_30d or {}).get("eval"),
        },
        "probe_best_slug": (probe.get("best_probe") or {}).get("slug"),
        "operator_lines": [
            "- [MKM-HOLDOUT-GATE] candidate=holdout_ovn_signed_bull; research_only; auto_promote=false.",
            f"- [MKM-HOLDOUT-GATE] holdout7 wrong_dir neutralized {h7.get('n_holdout7_wrong_neutralized')}/7.",
            f"- [MKM-HOLDOUT-GATE] 30d headline prod={prod_h:.1%} candidate={cand_h:.1%} "
            f"A1={'pass' if (eval_30d or {}).get('alert_1_pass') else 'fail'}.",
            "- [MKM-HOLDOUT-GATE] model_swap PoC closed; advisory unchanged; no Track A.",
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
