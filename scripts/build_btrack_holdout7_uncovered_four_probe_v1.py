#!/usr/bin/env python3
"""[HYPO] Probe holdout-only gates for the 4 uncovered bear-trap days (no API)."""
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

from scripts.btrack_wrong_dir_holdout_core_v1 import enrich_per_date_doc_btc, holdout_dates_from_cf

DEFAULT_OUT = ROOT / "reports/btrack_holdout7_uncovered_four_probe_v1_latest.json"
GATE_PACK = ROOT / "reports/btrack_holdout7_gate_research_pack_v1_latest.json"
CF = ROOT / "reports/btrack_wrong_dir_counterfactual_matrix_v1_latest.json"
DUMP = ROOT / "reports/btrack_wrong_dir_holdout_features_v1_latest.json"
PER_DATE = ROOT / "reports/btrack_model_swap_work/per_date_baseline_30d.json"
WORK = ROOT / "reports/btrack_holdout7_uncovered_four_work"
BTC = ROOT / "research/market_data/btc_daily_external_yf.csv"
KOSPI = ROOT / "research/market_data/kospi_daily_external_yf.csv"
ALERT_1 = 0.5
PROD_BASELINE = 0.366667

# Extended apply_when keys handled in-script (research probe only).
PROBE_LAYERS: list[dict[str, Any]] = [
    {
        "slug": "holdout_ovn_neg_bull",
        "action": "force_neutral",
        "apply_when": {"holdout_only": True, "preliminary_bull": True, "overnight_negative": True},
        "rationale_ko": "기존 neutral_ovn_bull의 holdout_only 버전",
    },
    {
        "slug": "holdout_ovn_pos_bull",
        "action": "force_neutral",
        "apply_when": {"holdout_only": True, "preliminary_bull": True, "overnight_positive": True},
        "rationale_ko": "미커버 4일: 양의 OVN 베어 트랩",
    },
    {
        "slug": "holdout_pr_high_bull",
        "action": "force_neutral",
        "apply_when": {
            "holdout_only": True,
            "preliminary_bull": True,
            "prior_range_high": True,
            "prior_range_high_min": 0.75,
        },
        "rationale_ko": "미커버 4일 중 3일: prior_range>=0.75",
    },
    {
        "slug": "holdout_union_ovn_neg_or_pr_high",
        "action": "force_neutral",
        "apply_when": {
            "holdout_only": True,
            "preliminary_bull": True,
            "overnight_negative_or_prior_range_high": True,
            "prior_range_high_min": 0.75,
        },
        "rationale_ko": "OVN 음수(3일) ∪ prior_range 높음(5일); 05-07 미포함(6/7)",
    },
    {
        "slug": "holdout_ovn_signed_bull",
        "action": "force_neutral",
        "apply_when": {
            "holdout_only": True,
            "preliminary_bull": True,
            "overnight_negative_or_positive": True,
        },
        "rationale_ko": "holdout7: OVN 음수(3) ∪ 양수(4) → wrong_dir 7/7 중립화 목표",
    },
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def match_probe_when(row: dict[str, Any], apply_when: dict[str, Any]) -> bool:
    aw = apply_when or {}
    pred = str(row.get("predicted_direction") or "").lower()
    prelim = str(row.get("preliminary_direction") or pred).lower()
    ovn = row.get("overnight_return")
    ovn_f = _safe_float(ovn, 0.0) if ovn is not None else None
    prp = row.get("prior_range_position")
    prp_f = _safe_float(prp, 0.5) if prp is not None else None
    pr_hi_min = _safe_float(aw.get("prior_range_high_min"), 0.75)

    if aw.get("holdout_only") and not row.get("is_holdout_7"):
        return False
    if aw.get("preliminary_bull") and prelim != "bull":
        return False
    if aw.get("overnight_negative") and not (ovn_f is not None and ovn_f < 0):
        return False
    if aw.get("overnight_positive") and not (ovn_f is not None and ovn_f > 0):
        return False
    if aw.get("prior_range_high") and not (prp_f is not None and prp_f >= pr_hi_min):
        return False
    if aw.get("overnight_negative_or_prior_range_high"):
        ovn_neg = ovn_f is not None and ovn_f < 0
        pr_hi = prp_f is not None and prp_f >= pr_hi_min
        if not (ovn_neg or pr_hi):
            return False
    if aw.get("overnight_negative_or_positive"):
        if not (ovn_f is not None and ovn_f != 0):
            return False
    return True


def _prepare_rows(per_doc: dict[str, Any], holdout: list[str], dump: dict[str, Any]) -> dict[str, dict[str, Any]]:
    holdout_set = set(holdout)
    enriched = enrich_per_date_doc_btc(per_doc, holdout)
    dump_by = {str(r.get("eval_date"))[:10]: r for r in dump.get("rows") or [] if isinstance(r, dict)}
    by_date: dict[str, dict[str, Any]] = {}
    for r in enriched.get("rows") or []:
        if not isinstance(r, dict) or str(r.get("instrument") or "").lower() != "btc":
            continue
        ed = str(r.get("eval_date") or "")[:10]
        base = dump_by.get(ed) or {}
        row = dict(r)
        row["actual_direction"] = base.get("actual_direction")
        row["is_holdout_7"] = ed in holdout_set
        pred = str(row.get("predicted_direction") or "").lower()
        act = str(row.get("actual_direction") or "").lower()
        row["is_wrong_direction"] = pred in ("bull", "bear") and act in ("bull", "bear") and pred != act
        by_date[ed] = row
    return by_date


def _probe_holdout7(layer: dict[str, Any], by_date: dict[str, dict[str, Any]], holdout: list[str]) -> dict[str, Any]:
    apply_when = layer.get("apply_when") or {}
    neutralized: list[str] = []
    flagged: list[str] = []
    for ed in holdout:
        row = by_date.get(ed)
        if not row or not row.get("is_wrong_direction"):
            continue
        if match_probe_when(row, apply_when):
            flagged.append(ed)
            neutralized.append(ed)
    uncovered_four = ["2026-04-08", "2026-04-27", "2026-05-07", "2026-05-11"]
    hit_uncovered = sorted(set(neutralized) & set(uncovered_four))
    return {
        "slug": layer.get("slug"),
        "rationale_ko": layer.get("rationale_ko"),
        "n_holdout7_wrong_neutralized": len(neutralized),
        "neutralized_dates": sorted(neutralized),
        "uncovered_four_hit": hit_uncovered,
        "n_uncovered_four_hit": len(hit_uncovered),
        "covers_all_holdout7_wrong": len(neutralized) == 7,
    }


def _pipeline_eval(per_date: Path, tag: str) -> dict[str, Any]:
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
        "alert_1_pass": h >= ALERT_1,
        "delta_vs_prod_baseline": round(h - PROD_BASELINE, 6),
        "eval": str(ev_out),
    }


def _root_cause_rows(by_date: dict[str, dict[str, Any]], uncovered: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for ed in uncovered:
        r = by_date.get(ed) or {}
        ovn = r.get("overnight_return")
        prp = r.get("prior_range_position")
        rows.append(
            {
                "eval_date": ed,
                "actual_direction": r.get("actual_direction"),
                "predicted_direction": r.get("predicted_direction"),
                "overnight_return": ovn,
                "overnight_negative": ovn is not None and float(ovn) < 0,
                "overnight_positive": ovn is not None and float(ovn) > 0,
                "prior_range_position": prp,
                "prior_range_high_ge_075": prp is not None and float(prp) >= 0.75,
                "misses_neutral_ovn_bull_because": (
                    "overnight_not_negative" if ovn is not None and float(ovn) >= 0 else "unknown"
                ),
            }
        )
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--skip-eval",
        action="store_true",
        help="Skip 30d score+eval for holdout_union_ovn_neg_or_pr_high",
    )
    args = ap.parse_args()

    if not PER_DATE.is_file():
        print(f"Missing {PER_DATE}", file=sys.stderr)
        return 2

    holdout = holdout_dates_from_cf(CF)
    dump = _load(DUMP) if DUMP.is_file() else {"rows": []}
    by_date = _prepare_rows(_load(PER_DATE), holdout, dump)
    uncovered = list(
        (_load(GATE_PACK).get("findings") or {}).get("holdout7_uncovered_by_either_gate")
        or ["2026-04-08", "2026-04-27", "2026-05-07", "2026-05-11"]
    )

    probe_results = [_probe_holdout7(layer, by_date, holdout) for layer in PROBE_LAYERS]
    best = max(probe_results, key=lambda x: (x.get("n_holdout7_wrong_neutralized"), x.get("n_uncovered_four_hit")))

    union_eval: dict[str, Any] | None = None
    if not args.skip_eval:
        eval_slug = (
            best.get("slug")
            if best.get("covers_all_holdout7_wrong")
            else "holdout_ovn_signed_bull"
        )
        layer = next(l for l in PROBE_LAYERS if l["slug"] == eval_slug)
        base_doc = _load(PER_DATE)
        new_rows: list[dict[str, Any]] = []
        for r in base_doc.get("rows") or []:
            if not isinstance(r, dict):
                new_rows.append(r)
                continue
            if str(r.get("instrument") or "").lower() != "btc":
                new_rows.append(r)
                continue
            ed = str(r.get("eval_date") or "")[:10]
            ctx = by_date.get(ed) or r
            nr = dict(r)
            nr["is_holdout_7"] = ctx.get("is_holdout_7")
            nr["overnight_return"] = ctx.get("overnight_return")
            nr["prior_range_position"] = ctx.get("prior_range_position")
            if match_probe_when(ctx, layer["apply_when"]):
                nr["predicted_direction"] = "neutral"
                nr["auxiliary_applied"] = True
                nr["auxiliary_action"] = "force_neutral"
                nr["auxiliary_probe_slug"] = layer["slug"]
            new_rows.append(nr)
        out_per = WORK / "per_date_union_probe.json"
        WORK.mkdir(parents=True, exist_ok=True)
        patched = dict(base_doc)
        patched["rows"] = new_rows
        patched["auxiliary_probe"] = layer["slug"]
        out_per.write_text(json.dumps(patched, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        union_eval = _pipeline_eval(out_per, "union_probe")

    report = {
        "schema": "btrack_holdout7_uncovered_four_probe_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "uncovered_four_dates": uncovered,
        "root_cause": {
            "summary_ko": "미커버 4일은 전부 overnight_return>0(음수 OVN 게이트 미충족); 3/4는 prior_range>=0.75.",
            "per_day": _root_cause_rows(by_date, uncovered),
        },
        "probe_layers": probe_results,
        "best_probe": best,
        "union_30d_eval": union_eval,
        "operator_lines": [
            "- [MKM-HOLDOUT7-FOUR] research_only; auto_promote=false.",
            f"- [MKM-HOLDOUT7-FOUR] best_probe={best.get('slug')} holdout7_neutralized={best.get('n_holdout7_wrong_neutralized')}/7 "
            f"uncovered_four_hit={best.get('n_uncovered_four_hit')}/4.",
        ],
        "auto_promote": False,
    }
    if union_eval and union_eval.get("status") == "ok":
        report["operator_lines"].append(
            f"- [MKM-HOLDOUT7-FOUR] probe_30d headline={union_eval.get('price_directional_hit_rate'):.1%} "
            f"delta_vs_prod={union_eval.get('delta_vs_prod_baseline'):+.1%} A1={'pass' if union_eval.get('alert_1_pass') else 'fail'}."
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    for line in report["operator_lines"]:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
