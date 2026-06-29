#!/usr/bin/env python3
"""[HYPO] Oper 30d vs research 180d panel reconcile (Type-A guard + score paths)."""
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

from scripts.apply_btrack_btc_typea_guard_to_score_v1 import apply_typea_guard, _load

DEFAULT_OUT = ROOT / "reports/btrack_oper_30d_180d_panel_reconcile_v1_latest.json"

RECOMMENDED_180 = ROOT / "reports/btrack_prophecy_score_recommended_eval_chain_v1_latest.json"
DUAL_180 = ROOT / "reports/btrack_ensemble_per_date_directions_180d_v1_latest.json"
OPER_30 = ROOT / "docs/final/artifacts/btrack_prophecy_score_latest.json"
DUAL_OPER = ROOT / "reports/btrack_ensemble_per_date_directions_dual_v1_latest.json"
FROZEN_KPI_30 = ROOT / "reports/btrack_prophecy_score_30d_frozen_kpi_a_v1.json"
POLICY = ROOT / "docs/final/artifacts/btrack_btc_typea_guard_v1.json"
APPLY_180_ART = ROOT / "reports/btrack_btc_lane2_typea_apply_recommended_180d_v1_latest.json"
APPLY_30_ART = ROOT / "reports/btrack_btc_typea_guard_apply_summary_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    try:
        return str(p.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(p)


def _btc_dates(score_doc: dict[str, Any]) -> list[str]:
    dates = sorted(
        {
            str(r.get("eval_date"))[:10]
            for r in (score_doc.get("rows") or [])
            if isinstance(r, dict) and str(r.get("instrument")).lower() == "btc"
        }
    )
    return dates


def _slice_score_last_n_days(score_doc: dict[str, Any], n: int) -> dict[str, Any]:
    btc_dates = _btc_dates(score_doc)
    if not btc_dates:
        return score_doc
    keep = set(btc_dates[-n:])
    out = json.loads(json.dumps(score_doc))
    out["rows"] = [
        r
        for r in (out.get("rows") or [])
        if isinstance(r, dict) and str(r.get("eval_date"))[:10] in keep
    ]
    inp = out.setdefault("inputs", {})
    if isinstance(inp, dict):
        inp["recent_trading_days"] = n
        inp["panel_reconcile_slice"] = f"last_{n}_btc_eval_dates"
    return out


def _apply_summary(
    label: str,
    score_path: Path,
    dual_path: Path,
    *,
    score_lt: float,
    kospi_mode: str,
    policy_id: str,
) -> dict[str, Any]:
    score_doc = _load(score_path)
    dual_doc = _load(dual_path)
    _, changes, summary = apply_typea_guard(
        score_doc,
        dual_doc,
        score_lt=score_lt,
        kospi_mode=kospi_mode,
        policy_id=policy_id,
    )
    btc_dates = _btc_dates(score_doc)
    return {
        "label": label,
        "score_json": _rel(score_path),
        "dual_json": _rel(dual_path),
        "btc_date_range": [btc_dates[0], btc_dates[-1]] if btc_dates else None,
        "n_btc_eval_dates": len(btc_dates),
        "recent_trading_days_input": (score_doc.get("inputs") or {}).get("recent_trading_days"),
        "per_date_direction_json": (score_doc.get("inputs") or {}).get("per_date_direction_json"),
        **summary,
        "change_dates": [c.get("eval_date") for c in changes],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    policy = _load(POLICY)
    score_lt = float(policy.get("score_lt", 0.12))
    kospi_mode = str(policy.get("kospi_mode", "bull_only"))
    policy_id = str(policy.get("policy_id", "type_a_bull_bear_score12_kospi_bull"))

    rec180 = _load(RECOMMENDED_180)
    rec30_slice = _slice_score_last_n_days(rec180, 30)

    tmp30 = ROOT / "reports/tmp_panel_reconcile_recommended_last30_v1.json"
    tmp30.parent.mkdir(parents=True, exist_ok=True)
    tmp30.write_text(json.dumps(rec30_slice, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    panels = {
        "oper_headline_30d": _apply_summary(
            "oper_headline_30d",
            OPER_30,
            DUAL_OPER,
            score_lt=score_lt,
            kospi_mode=kospi_mode,
            policy_id=policy_id,
        ),
        "recommended_180d_prod_aligned": _apply_summary(
            "recommended_180d_prod_aligned",
            RECOMMENDED_180,
            DUAL_180,
            score_lt=score_lt,
            kospi_mode=kospi_mode,
            policy_id=policy_id,
        ),
        "recommended_last30_from_180d_score": _apply_summary(
            "recommended_last30_from_180d_score",
            tmp30,
            DUAL_180,
            score_lt=score_lt,
            kospi_mode=kospi_mode,
            policy_id=policy_id,
        ),
    }

    frozen30 = _load(FROZEN_KPI_30)
    apply180 = _load(APPLY_180_ART)
    apply30 = _load(APPLY_30_ART)

    dates_180 = set(panels["recommended_180d_prod_aligned"].get("change_dates") or [])
    dates_oper30 = set(panels["oper_headline_30d"].get("change_dates") or [])
    dates_rec30 = set(panels["recommended_last30_from_180d_score"].get("change_dates") or [])

    oper_btc_dates = set(_btc_dates(_load(OPER_30)))
    overlap_180_in_oper30 = sorted(dates_180 & oper_btc_dates)
    overlap_180_in_rec30 = sorted(dates_180 & set(_btc_dates(rec30_slice)))

    verdict_ko = (
        "oper 30d headline n_changes=0은 score/dual/per-date 경로 불일치 + 30d 창에 Type-A trigger row 부재 가능. "
        "recommended 180d 동일 정책은 n_changes=16; last-30 slice of recommended score도 별도 집계."
    )

    ledger = (
        "Panel reconcile: oper 30d Type-A n_changes=0 vs recommended 180d n_changes=16 — "
        "different score SSOT/dual/window; not oper promotion evidence."
    )

    report: dict[str, Any] = {
        "schema": "btrack_oper_30d_180d_panel_reconcile_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "track_a_auto_promote": False,
        "send_gate": "HOLD",
        "type_a_policy": {"policy_id": policy_id, "score_lt": score_lt, "kospi_mode": kospi_mode},
        "frozen_kpi_a_30d_anchor": {
            "artifact": _rel(FROZEN_KPI_30),
            "eval_date": frozen30.get("eval_date"),
            "recent_trading_days": (frozen30.get("inputs") or {}).get("recent_trading_days"),
            "neutral_bps": frozen30.get("neutral_bps"),
        },
        "panels": panels,
        "stored_apply_artifacts": {
            "oper_30d_summary": {
                "artifact": _rel(APPLY_30_ART),
                "n_changes": apply30.get("n_changes"),
                "delta_hit_rate": apply30.get("delta_hit_rate"),
                "score_json": (apply30.get("inputs") or {}).get("score_json"),
            },
            "recommended_180d_apply": {
                "artifact": _rel(APPLY_180_ART),
                "n_changes": apply180.get("n_changes"),
                "delta_hit_rate": apply180.get("delta_hit_rate"),
            },
        },
        "change_date_analysis": {
            "recommended_180d_change_dates": sorted(dates_180),
            "oper_30d_change_dates": sorted(dates_oper30),
            "recommended_last30_slice_change_dates": sorted(dates_rec30),
            "recommended_180d_dates_inside_oper_30d_window": overlap_180_in_oper30,
            "recommended_180d_dates_inside_rec30_slice": overlap_180_in_rec30,
            "n_180_changes_outside_oper_30d_window": len(dates_180 - oper_btc_dates),
        },
        "wf_vs_apply_note": {
            "calibration_pattern": "WF OOS optimistic delta != full-panel apply delta (Lane2 calibration)",
            "type_a_pattern": "Same policy; delta driven by panel rows meeting bull+score_lt+kospi_bull trigger",
        },
        "verdict_ko": verdict_ko,
        "ledger_line": ledger,
        "operator_lines": [
            "- [PANEL-RECON] research_only; oper recommended score NOT overwritten.",
            f"- [PANEL-RECON] oper_30d n_changes={panels['oper_headline_30d'].get('n_changes')} "
            f"recommended_180d n_changes={panels['recommended_180d_prod_aligned'].get('n_changes')}.",
            f"- [PANEL-RECON] recommended last-30 slice n_changes={panels['recommended_last30_from_180d_score'].get('n_changes')}.",
            f"- [PANEL-RECON] 180d change dates outside oper 30d window: "
            f"{len(dates_180 - oper_btc_dates)} of {len(dates_180)}.",
            "- [PANEL-RECON] Do not read oper 30d headline as contradicting 180d shadow +4.4pp.",
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
