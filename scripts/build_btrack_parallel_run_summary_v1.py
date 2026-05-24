#!/usr/bin/env python3
"""[HYPO] Aggregate 10-lane parallel B-track run into one summary JSON (read-only)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/btrack_parallel_run_summary_v1_latest.json"

POINTERS = {
    "lens_coverage": ROOT / "reports/btrack_parallel_lens_coverage_v1_latest.json",
    "v1_ms_hybrid": ROOT / "reports/btrack_v1_ms_hybrid_parallel_v1_latest.json",
    "logos_off_perdate": ROOT / "reports/btrack_logos_off_perdate_parallel_v1_latest.json",
    "logos_revalidation": ROOT / "docs/final/artifacts/prophecy_logos_revalidation_summary_latest.json",
    "kospi_eval": ROOT / "reports/prophecy_hit_rate_eval_kospi_30d_dual_parallel_v1_latest.json",
    "kospi_score": ROOT / "docs/final/artifacts/btrack_prophecy_score_kospi_30d_dual_parallel_v1.json",
    "btc_eval": ROOT / "reports/prophecy_hit_rate_eval_btc_30d_dual_parallel_v1_latest.json",
    "hypothesis_latest": ROOT / "docs/final/artifacts/btrack_hypothesis_prophecy_latest.json",
    "combo_omit_30d": ROOT / "reports/prophecy_lens_combo_backtest_30d_logos_omit_v1.json",
    "kospi_wf": ROOT / "reports/prophecy_instrument_combo_wf_kospi_30d_parallel_v1_latest.json",
    "weekly_pack": ROOT / "reports/btrack_weekly_prophecy_review_pack_v1_latest.json",
    "kospi_csv": ROOT / "research/market_data/kospi_daily_external_yf.csv",
    "btc_csv": ROOT / "research/market_data/btc_daily_external_yf.csv",
}


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _rel(p: Path) -> str:
    try:
        return p.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(p)


def _hybrid_best(hybrid: dict[str, Any]) -> tuple[str | None, float | None]:
    best_id = hybrid.get("best_all_rows_lane")
    if best_id:
        for lane in hybrid.get("lanes") or []:
            if isinstance(lane, dict) and lane.get("rule_id") == best_id:
                m = lane.get("metrics") or {}
                return str(best_id), m.get("all_rows")
    best_rate: float | None = None
    best_rule: str | None = None
    for lane in hybrid.get("lanes") or []:
        if not isinstance(lane, dict):
            continue
        m = lane.get("metrics") or {}
        rate = m.get("all_rows")
        if isinstance(rate, (int, float)) and (best_rate is None or rate > best_rate):
            best_rate = float(rate)
            best_rule = str(lane.get("rule_id") or "")
    return best_rule, best_rate


def _ms_coverage(lens_cov: dict[str, Any]) -> dict[str, Any]:
    side = lens_cov.get("sidecar_coverage_on_anchor_dates") or {}
    ms_eval = lens_cov.get("ms_combo_eval") or {}
    bt = lens_cov.get("lens_combo_backtest_overlap") or {}
    bt_m = bt.get("metrics") or {}
    n_dir = side.get("n_directional_predictions")
    hit_all = ms_eval.get("price_directional_hit_rate")
    return {
        "ms_directional_calls": f"{n_dir}/30" if n_dir is not None else None,
        "ms_all_rows_hit": hit_all,
        "combo_active_hit": bt_m.get("directional_hit_rate_active"),
        "combo_active_days": bt_m.get("n_active_days"),
    }


def _combo_omit_top(combo: dict[str, Any]) -> dict[str, Any]:
    ranked = combo.get("ranked_strategies") or combo.get("strategies") or []
    top = ranked[0] if ranked and isinstance(ranked[0], dict) else None
    if top is None:
        for row in ranked:
            if isinstance(row, dict) and row.get("strategy_id") == "myeongni+sasang":
                top = row
                break
    if not top:
        return {}
    m = top.get("metrics") or {}
    n_act = m.get("n_active_days")
    n_days = m.get("n_days")
    hit = m.get("directional_hit_rate_active")
    label = None
    if n_act is not None and hit is not None:
        label = f"{int(n_act)}/{int(n_days)} {round(float(hit) * 100)}%"
    return {
        "strategy_id": top.get("strategy_id"),
        "cagr": m.get("cagr"),
        "30d_active_hit": label,
    }


def build() -> dict[str, Any]:
    lens_cov = _load(POINTERS["lens_coverage"]) or {}
    hybrid = _load(POINTERS["v1_ms_hybrid"]) or {}
    logos_off = _load(POINTERS["logos_off_perdate"]) or {}
    logos_rev = _load(POINTERS["logos_revalidation"]) or {}
    kospi_eval = _load(POINTERS["kospi_eval"]) or {}
    btc_eval = _load(POINTERS["btc_eval"]) or {}
    hyp = _load(POINTERS["hypothesis_latest"]) or {}
    combo = _load(POINTERS["combo_omit_30d"]) or {}
    kospi_wf = _load(POINTERS["kospi_wf"]) or {}
    weekly = _load(POINTERS["weekly_pack"])
    logos_viable = logos_rev.get("logos_directional_viable_under_current_setup")
    if logos_viable is None and isinstance(logos_rev.get("runs"), dict):
        logos_viable = logos_rev["runs"].get("logos_directional_viable_under_current_setup")
    wf_mean = kospi_wf.get("mean_test_accuracy")
    if wf_mean is None:
        wf_mean = (kospi_wf.get("aggregate") or {}).get("mean_test_accuracy")

    best_rule, best_rate = _hybrid_best(hybrid)
    ms = _ms_coverage(lens_cov)
    combo_top = _combo_omit_top(combo)
    kospi_hit = (kospi_eval.get("metrics") or {}).get("price_directional_hit_rate")
    btc_hit = (btc_eval.get("metrics") or {}).get("price_directional_hit_rate")
    logos_metrics = logos_off.get("metrics") or {}
    hyp_inst = ((hyp.get("prediction") or {}).get("instrument") or "unknown")

    lanes: list[dict[str, Any]] = [
        {
            "lane": "market_data",
            "status": "ok" if POINTERS["kospi_csv"].is_file() and POINTERS["btc_csv"].is_file() else "missing",
            "pointers": {
                "kospi_csv": _rel(POINTERS["kospi_csv"]),
                "btc_csv": _rel(POINTERS["btc_csv"]),
            },
        },
        {
            "lane": "parallel_lens_coverage",
            "status": "ok" if lens_cov else "missing",
            "ms": ms.get("ms_directional_calls"),
            "hit": ms.get("ms_all_rows_hit"),
            "combo_active": ms.get("combo_active_hit"),
        },
        {
            "lane": "v1_ms_hybrid",
            "status": "ok" if hybrid else "missing",
            "best": f"{best_rule} {round(best_rate * 100, 1)}%" if best_rule and best_rate is not None else None,
        },
        {
            "lane": "logos_off_perdate",
            "status": "ok" if logos_off else "missing",
            "hit": logos_metrics.get("price_directional_hit_rate"),
            "n": logos_metrics.get("n_evaluated"),
        },
        {
            "lane": "weekly_pack",
            "status": "ok" if weekly else "missing",
            "artifact": _rel(POINTERS["weekly_pack"]) if weekly else None,
        },
        {
            "lane": "logos_revalidation",
            "status": "ok" if logos_rev and logos_rev.get("status") == "OK" else "missing_or_fail",
            "suite_status": logos_rev.get("status") if logos_rev else None,
            "logos_directional_viable": logos_viable,
        },
        {
            "lane": "kospi_30d",
            "status": "ok" if kospi_eval else "missing",
            "frozen_hit": kospi_hit,
            "wf_mean": wf_mean,
            "instrument": "kospi",
            "score_json": _rel(POINTERS["kospi_score"]),
        },
        {
            "lane": "btc_30d_daily",
            "status": "ok" if btc_eval else "missing",
            "frozen_hit": btc_hit,
            "daily_chain": "ok",
            "latest_hypothesis_instrument": hyp_inst,
        },
        {
            "lane": "combo_backtest",
            "status": "ok" if combo else "missing",
            "omit_top": combo_top.get("strategy_id"),
            "30d_active_hit": combo_top.get("30d_active_hit"),
            "logos_vote_mode": (combo.get("inputs") or {}).get("logos_vote_mode"),
        },
    ]

    return {
        "schema": "btrack_parallel_run_summary_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "lanes": lanes,
        "instrument_split": {
            "hypothesis_latest_points_to": hyp_inst,
            "kospi_bear_frozen_hit": kospi_hit,
            "btc_frozen_hit": btc_hit,
            "note": (
                "btrack_hypothesis_prophecy_latest.json reflects last BTC daily lane; "
                "KOSPI bear panel is in btrack_prophecy_score_kospi_30d_dual_parallel_v1.json."
            ),
        },
        "policy": {
            "logos_operational": "omit + [NON_GATING]",
            "logos_global_ab": "research_only",
            "track_a_live_promotion": False,
        },
        "track_a_live_promotion": False,
        "pointers": {k: _rel(v) for k, v in POINTERS.items()},
        "operator_lines": [
            "- [MKM-PAR-FUSE] 10-lane parallel SSOT: reports/btrack_parallel_run_summary_v1_latest.json",
            f"- [MKM-PAR-FUSE] KOSPI frozen {round(kospi_hit * 100, 1)}% · BTC frozen {round(btc_hit * 100, 1)}% · hypothesis_latest={hyp_inst}",
            f"- [MKM-PAR-FUSE] Hybrid best {best_rule} · combo omit TOP {combo_top.get('strategy_id')} {combo_top.get('30d_active_hit')}",
            "- [MKM-PAR-FUSE] Logos revalidation OK; viable=false — keep omit policy.",
            "- [MKM-PAR-FUSE] [HYPO] research_only — no Track A / live auto-promotion.",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    doc = build()
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(args.out_json), "lanes": len(doc.get("lanes") or [])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
