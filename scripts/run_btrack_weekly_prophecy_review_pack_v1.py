#!/usr/bin/env python3
"""[HYPO] Weekly B-track prophecy review pack — anchor 30d panel SSOT."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

ANCHOR_SCORE = ROOT / "reports/btrack_prophecy_score_30d_frozen_kpi_a_v1.json"
ANCHOR_DATES = ROOT / "reports/btrack_anchor_eval_dates_v1.json"
SIDECAR = ROOT / "reports/btrack_prophecy_score_insight_sidecar_anchor_30d_v1.json"
ALIGNED = ROOT / "reports/btrack_aligned_30d_experiment_v1_latest.json"
BTC = ROOT / "research/market_data/btc_daily_external_yf.csv"
HYP = ROOT / "docs/final/artifacts/btrack_hypothesis_prophecy_latest.json"
OUT = ROOT / "reports/btrack_weekly_prophecy_review_pack_v1_latest.json"
LENS_BT = ROOT / "reports/prophecy_lens_combo_backtest_anchor_30d_v1_latest.json"
MS_EVAL = ROOT / "reports/prophecy_hit_rate_eval_ms_anchor_v1_v2.json"
MATCHED = ROOT / "reports/btrack_active_day_matched_compare_v1_latest.json"
HYBRID = ROOT / "reports/btrack_v1_ms_hybrid_parallel_v1_latest.json"
ANCHOR_PROMO = ROOT / "reports/btrack_anchor_panel_promotion_parallel_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> None:
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    if cp.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)}\n{cp.stderr or cp.stdout}")


def _rel(p: Path) -> str:
    rp = p.resolve()
    try:
        return str(rp.relative_to(ROOT.resolve()))
    except ValueError:
        return str(rp)


def _metrics(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    m = json.loads(path.read_text(encoding="utf-8")).get("metrics") or {}
    return {
        "all_rows": m.get("price_directional_hit_rate"),
        "dir_only": m.get("price_hit_rate_on_directional_calls"),
        "n": m.get("n_evaluated"),
        "calls": m.get("n_directional_calls"),
        "neutral": m.get("n_neutral_predictions"),
    }


def _find_strategy(bt: dict[str, Any], sid: str) -> dict[str, Any] | None:
    for row in bt.get("ranked_strategies") or []:
        if isinstance(row, dict) and row.get("strategy_id") == sid:
            return row
    return None


def _ms_active_day_hit(score_path: Path, per_date_path: Path) -> dict[str, Any]:
    score = json.loads(score_path.read_text(encoding="utf-8"))
    per = json.loads(per_date_path.read_text(encoding="utf-8"))
    pred_by_date = {
        str(r["eval_date"])[:10]: str(r.get("predicted_direction") or "").lower()
        for r in per.get("rows") or []
        if isinstance(r, dict)
    }
    active_hits = 0
    active_n = 0
    for row in score.get("rows") or []:
        if str(row.get("instrument") or "").lower() != "btc":
            continue
        ed = str(row.get("eval_date") or "")[:10]
        pred = pred_by_date.get(ed, "neutral")
        actual = str(row.get("actual_direction") or "").lower()
        if pred not in ("bull", "bear"):
            continue
        active_n += 1
        if pred == actual:
            active_hits += 1
    rate = round(active_hits / active_n, 6) if active_n else None
    return {"n_active_days": active_n, "hits": active_hits, "directional_hit_rate_active": rate}


def main() -> int:
    py = sys.executable
    per_date_ms = ROOT / "reports/btrack_lens_combo_ms_per_date_anchor_v1.json"

    if not MATCHED.is_file():
        _run([py, "scripts/run_btrack_active_day_matched_compare_v1.py"])

    _run(
        [
            py,
            "scripts/run_prophecy_lens_combo_backtest_v1.py",
            "--score-json",
            _rel(ANCHOR_SCORE),
            "--sidecar-json",
            _rel(SIDECAR),
            "--target-instrument",
            "btc",
            "--logos-vote-mode",
            "omit",
            "--output",
            _rel(LENS_BT),
        ]
    )

    if not per_date_ms.is_file() or not MS_EVAL.is_file():
        _run(
            [
                py,
                "scripts/build_btrack_lens_combo_myeongni_sasang_per_date_v1.py",
                "--score-json",
                _rel(ANCHOR_SCORE),
                "--sidecar-json",
                _rel(SIDECAR),
                "--output",
                _rel(per_date_ms),
            ]
        )
        ms_score = ROOT / "reports/btrack_prophecy_score_ms_anchor_weekly_v1.json"
        _run(
            [
                py,
                "scripts/build_btrack_prophecy_score_from_ohlcv.py",
                "--btc-csv",
                _rel(BTC),
                "--hypothesis-json",
                _rel(HYP),
                "--batch-eval-dates-json",
                _rel(ANCHOR_DATES),
                "--per-date-direction-json",
                _rel(per_date_ms),
                "--output",
                _rel(ms_score),
            ]
        )
        _run(
            [
                py,
                "scripts/eval_prophecy_hit_rate_v1.py",
                "--run-mode",
                "price",
                "--score-json",
                _rel(ms_score),
                "--headline-instrument",
                "btc",
                "--output",
                _rel(MS_EVAL),
            ]
        )

    bt = json.loads(LENS_BT.read_text(encoding="utf-8")) if LENS_BT.is_file() else {}
    ms_row = _find_strategy(bt, "myeongni+sasang")
    logos_row = _find_strategy(bt, "logos+myeongni+sasang")

    aligned = json.loads(ALIGNED.read_text(encoding="utf-8")) if ALIGNED.is_file() else {}
    lanes = {r["lane"]: r.get("metrics") for r in aligned.get("lanes") or [] if isinstance(r, dict)}
    matched = json.loads(MATCHED.read_text(encoding="utf-8")) if MATCHED.is_file() else {}
    hybrid = json.loads(HYBRID.read_text(encoding="utf-8")) if HYBRID.is_file() else {}
    anchor_promo = json.loads(ANCHOR_PROMO.read_text(encoding="utf-8")) if ANCHOR_PROMO.is_file() else {}

    pack = {
        "schema": "btrack_weekly_prophecy_review_pack_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "anchor_panel": {
            "score": _rel(ANCHOR_SCORE),
            "dates_json": _rel(ANCHOR_DATES),
            "n_days": len(json.loads(ANCHOR_DATES.read_text(encoding="utf-8")).get("eval_dates") or []),
        },
        "headline_frozen_kpi_a": lanes.get("anchor_snapshot_on_disk"),
        "candidates": {
            "v1_per_date_ensemble": {
                "metrics": lanes.get("v1_per_date_same_dates"),
                "recommendation": "primary_btrack_uplift_candidate",
            },
            "kpi_b_walkforward": {
                "metrics": lanes.get("kpi_b_walkforward_same_dates"),
                "recommendation": "shadow_only_not_headline",
            },
            "ms_myeongni_sasang_per_date": {
                "price_eval": _metrics(MS_EVAL),
                "active_day": _ms_active_day_hit(
                    ROOT / "reports/btrack_prophecy_score_ms_anchor_v1_v2.json"
                    if (ROOT / "reports/btrack_prophecy_score_ms_anchor_v1_v2.json").is_file()
                    else ROOT / "reports/btrack_prophecy_score_ms_anchor_weekly_v1.json",
                    per_date_ms,
                ),
                "backtest_myeongni_sasang": (ms_row or {}).get("metrics"),
            },
            "lens_combo_logos_plus": {
                "backtest": (logos_row or {}).get("metrics"),
                "note": "ranking winner on CAGR; not same as MS-only per-date.",
            },
        },
        "active_day_matched": {
            "artifact": _rel(MATCHED) if MATCHED.is_file() else None,
            "panel": matched.get("panel"),
            "lanes": matched.get("lanes"),
        },
        "v1_ms_hybrid_parallel": {
            "artifact": _rel(HYBRID) if HYBRID.is_file() else None,
            "best_all_rows_lane": hybrid.get("best_all_rows_lane"),
            "lanes_summary": [
                {
                    "rule_id": lane.get("rule_id"),
                    "metrics": lane.get("metrics"),
                    "error": lane.get("error"),
                }
                for lane in hybrid.get("lanes") or []
                if isinstance(lane, dict)
            ],
        },
        "anchor_promotion_wf_gates": {
            "artifact": _rel(ANCHOR_PROMO) if ANCHOR_PROMO.is_file() else None,
            "combined_pass_count": anchor_promo.get("lanes_combined_pass_count"),
            "lanes": [
                {
                    "lane_id": lane.get("lane_id"),
                    "wf_mean": (lane.get("walkforward") or {}).get("mean_test_accuracy"),
                    "combined_all_passed": (lane.get("promotion_gates") or {}).get(
                        "combined_all_passed"
                    ),
                    "outcome_class": (lane.get("promotion_gates") or {}).get("outcome_class"),
                }
                for lane in anchor_promo.get("lanes") or []
                if isinstance(lane, dict)
            ],
        },
        "decision_gates": {
            "production_min_direction_confidence": 0.18,
            "track_a_auto_promotion": False,
            "compare_same_scoring_mode": "per_date_direction_overrides on anchor_eval_dates only",
        },
        "operator_lines": [
            "- [MKM-WEEKLY-B] Frozen KPI-A bear batch: 43.3% (30d) — operational headline unchanged.",
            "- [MKM-WEEKLY-B] v1 per-date on same 30d: 56.7% all / 58.6% dir-only — weekly review lead candidate.",
            "- [MKM-WEEKLY-B] MS myeongni+sasang: use directional_hit_rate_active from backtest vs dir-only on price eval.",
            "- [MKM-WEEKLY-B] Do not promote from canvas/backtest alone; human gate required.",
        ],
    }
    if matched.get("lanes"):
        m_lanes = matched["lanes"]
        v1m = (m_lanes.get("v1_per_date_on_ms_active") or {}).get("directional_hit_rate")
        msm = (m_lanes.get("ms_on_ms_active") or {}).get("directional_hit_rate")
        pack["operator_lines"].append(
            f"- [MKM-WEEKLY-B] MS-active matched subset: v1={v1m} vs MS={msm} (same {matched.get('panel', {}).get('ms_active_days')} days)."
        )
    if anchor_promo.get("lanes"):
        n_pass = anchor_promo.get("lanes_combined_pass_count", 0)
        pack["operator_lines"].append(
            f"- [MKM-WEEKLY-B] Anchor WF promotion gates: {n_pass}/3 combined_pass "
            "(hit-rate uplift ≠ WF strict pass on 30d panel)."
        )
    if hybrid.get("best_all_rows_lane"):
        best_h = hybrid.get("best_all_rows_lane")
        for lane in hybrid.get("lanes") or []:
            if isinstance(lane, dict) and lane.get("rule_id") == best_h:
                hm = lane.get("metrics") or {}
                pack["operator_lines"].append(
                    f"- [MKM-WEEKLY-B] Hybrid best all-rows: {best_h}={hm.get('all_rows')} "
                    f"(v1 solo 0.566667; still below MS dir-only 0.692 on 13 calls)."
                )
                break
    OUT.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {OUT.resolve()}")
    ms_m = (ms_row or {}).get("metrics") or {}
    print(f"MS backtest active: {ms_m.get('directional_hit_rate_active')} n_active={ms_m.get('n_active_days')}")
    v1 = lanes.get("v1_per_date_same_dates") or {}
    print(f"v1 per-date: {v1.get('price_directional_hit_rate')} dir={v1.get('price_hit_rate_on_directional_calls')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
