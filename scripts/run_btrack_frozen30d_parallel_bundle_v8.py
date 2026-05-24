#!/usr/bin/env python3
"""[HYPO] Parallel bundle v8: holdout7 miss autopsy, BBS+MS candidate manifest, stack leaderboard."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_OUT = ROOT / "reports/btrack_frozen30d_parallel_bundle_v8_latest.json"
WORK = ROOT / "reports/btrack_frozen30d_parallel_bundle_v8_work"
HOLDOUT7_PANEL = ROOT / "reports/btrack_frozen30d_holdout7_scored_panel_v1_latest.json"
DAILY_DIFF = ROOT / "reports/btrack_frozen30d_hybrid_daily_diff_v1_latest.json"
FEATURES = ROOT / "reports/btrack_wrong_dir_holdout_features_v1_latest.json"
BBS_HYBRID_PER = ROOT / "reports/btrack_frozen30d_parallel_bundle_v6_work/per_date_bull_bear_split_hybrid_hybrid.json"
if not BBS_HYBRID_PER.is_file():
    BBS_HYBRID_PER = ROOT / "reports/btrack_frozen30d_parallel_bundle_v6_work/per_date_bull_bear_split_hybrid.json"
LEGACY_HYBRID_PER = ROOT / "reports/btrack_v1_ms_hybrid_work/agree_or_ms_else_v1/per_date.json"
REC_CHAIN = ROOT / "scripts/run_prophecy_btrack_recommended_eval_chain_v1.py"
HYBRID_180D = ROOT / "reports/btrack_hybrid_180d_promotion_parallel_v1_latest.json"
FROZEN_KPI_A = 0.433333

HOLDOUT7 = frozenset(
    {
        "2026-04-02",
        "2026-04-08",
        "2026-04-14",
        "2026-04-24",
        "2026-04-27",
        "2026-05-07",
        "2026-05-11",
    }
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _per_day_map(lane: str) -> dict[str, dict[str, Any]]:
    panel = _load(HOLDOUT7_PANEL)
    days = (panel.get("lanes") or {}).get(lane, {}).get("holdout7", {}).get("per_day") or []
    return {str(d["eval_date"])[:10]: d for d in days if isinstance(d, dict)}


def _diff_map() -> dict[str, dict[str, Any]]:
    return {
        str(d["eval_date"])[:10]: d
        for d in (_load(DAILY_DIFF).get("per_day") or [])
        if isinstance(d, dict)
    }


def _feat_map() -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    if FEATURES.is_file():
        for row in _load(FEATURES).get("rows") or []:
            if isinstance(row, dict):
                ed = str(row.get("eval_date") or "")[:10]
                if ed:
                    out[ed] = row
    return out


def _hybrid_sources(per_path: Path) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for row in _load(per_path).get("rows") or []:
        if not isinstance(row, dict):
            continue
        ed = str(row.get("eval_date") or "")[:10]
        src = row.get("sources") if isinstance(row.get("sources"), dict) else {}
        out[ed] = {
            "v1": str(src.get("v1") or row.get("predicted_direction") or "neutral").lower(),
            "ms": str(src.get("ms") or "neutral").lower(),
            "hybrid": str(row.get("predicted_direction") or "neutral").lower(),
            "resolver": (row.get("v1_resolver") or {}).get("mode") if isinstance(row.get("v1_resolver"), dict) else None,
        }
    return out


def _task_holdout7_miss_autopsy() -> dict[str, Any]:
    if not HOLDOUT7_PANEL.is_file():
        return {"task": "holdout7_miss_autopsy", "exit_code": 2, "error": "missing holdout7 panel"}

    bbs_days = _per_day_map("bbs_hybrid")
    m016_days = _per_day_map("m016_solo")
    diff = _diff_map()
    feat = _feat_map()
    bbs_src = _hybrid_sources(BBS_HYBRID_PER) if BBS_HYBRID_PER.is_file() else {}

    misses: list[dict[str, Any]] = []
    hits: list[str] = []
    for ed in sorted(HOLDOUT7):
        bbs = bbs_days.get(ed, {})
        if bbs.get("hit"):
            hits.append(ed)
            continue
        d = diff.get(ed, {})
        f = feat.get(ed, {})
        src = bbs_src.get(ed, {})
        misses.append(
            {
                "eval_date": ed,
                "actual": bbs.get("actual") or d.get("actual"),
                "bbs_hybrid_pred": bbs.get("pred"),
                "m016_solo_pred": (m016_days.get(ed) or {}).get("pred"),
                "legacy_v1": d.get("legacy_v1"),
                "m016_v1": d.get("m016_v1"),
                "legacy_ms": d.get("legacy_ms"),
                "m016_ms": d.get("m016_ms"),
                "bbs_v1_resolved": src.get("v1"),
                "bbs_ms": src.get("ms"),
                "pattern_legacy_bull_m016_bear": d.get("legacy_v1") == "bull" and d.get("m016_v1") == "bear",
                "overnight_return": f.get("overnight_return"),
                "prior_range_position": f.get("prior_range_position"),
                "preliminary_direction": f.get("preliminary_direction"),
                "is_holdout_7": f.get("is_holdout_7"),
                "miss_driver": _miss_driver(d, bbs.get("pred"), src),
            }
        )

    cohort = {
        "all_miss_same_root": all(m.get("miss_driver") == "v1_bull_ms_neutral_on_bear_day" for m in misses),
        "n_miss": len(misses),
        "n_hit": len(hits),
        "hit_dates": hits,
    }

    out = ROOT / "reports/btrack_frozen30d_holdout7_miss_autopsy_v1_latest.json"
    report = {
        "schema": "btrack_frozen30d_holdout7_miss_autopsy_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "holdout7_dates": sorted(HOLDOUT7),
        "lane": "bbs_ms_hybrid",
        "holdout7_hit_rate": round(len(hits) / 7, 6),
        "cohort_summary": cohort,
        "misses": misses,
        "recommendation": (
            "Holdout7 misses are uniformly legacy/m016 v1 bull with MS neutral → hybrid bull on bear days. "
            "Resolver does not fire; need MS active bear or v1 bear — not fixable by bull_bear_split alone."
        ),
    }
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"task": "holdout7_miss_autopsy", "exit_code": 0, "report": str(out), "summary": cohort}


def _miss_driver(diff: dict[str, Any], pred: str | None, src: dict[str, str]) -> str:
    act = str(diff.get("actual") or "").lower()
    if act != "bear":
        return "other"
    v1 = src.get("v1") or diff.get("m016_v1")
    ms = src.get("ms") or diff.get("m016_ms")
    if v1 == "bull" and ms in ("neutral", ""):
        return "v1_bull_ms_neutral_on_bear_day"
    if v1 == "bull" and ms == "bull":
        return "v1_and_ms_bull_on_bear"
    return "other"


def _task_bbs_candidate_manifest() -> dict[str, Any]:
    panel = _load(HOLDOUT7_PANEL) if HOLDOUT7_PANEL.is_file() else {}
    lanes = panel.get("lanes") or {}
    bbs_h = lanes.get("bbs_hybrid", {})
    h180 = _load(HYBRID_180D) if HYBRID_180D.is_file() else {}

    manifest = {
        "schema": "btrack_bbs_ms_hybrid_candidate_manifest_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "track_a_auto_promote": False,
        "combined_all_passed": False,
        "candidate_id": "bbs_resolver_margin016_v1_plus_ms_agree_or_ms_else_v1",
        "description_ko": (
            "margin_016 v1에 legacy_bull∧m016_bear일 때 legacy v1로 치환한 뒤 "
            "MS agree_or_ms_else_v1 하이브리드 적용"
        ),
        "rules": {
            "v1_resolver": {
                "when": {"legacy_v1": "bull", "margin_016_v1": "bear"},
                "then": "use_legacy_v1",
                "else": "use_margin_016_v1",
            },
            "hybrid": "agree_or_ms_else_v1",
        },
        "paths": {
            "margin_016_per_date": "reports/btrack_frozen30d_margin_fine_sweep_work/per_date_margin_016.json",
            "legacy_v1_per_date": "reports/btrack_ensemble_per_date_v1_prod_perdate_30d_v1.json",
            "bbs_hybrid_per_date": str(BBS_HYBRID_PER.relative_to(ROOT)).replace("\\", "/"),
            "ms_per_date": "reports/btrack_lens_combo_ms_per_date_anchor_v1.json",
        },
        "metrics_frozen_30d_btc": {
            "frozen_kpi_a_baseline": FROZEN_KPI_A,
            "bbs_ms_hybrid_all_rows": (bbs_h.get("full_30d") or {}).get("price_directional_hit_rate"),
            "bbs_ms_hybrid_holdout7": (bbs_h.get("holdout7") or {}).get("price_directional_hit_rate"),
            "bbs_solo_holdout7": (lanes.get("bbs_solo", {}).get("holdout7") or {}).get(
                "price_directional_hit_rate"
            ),
            "delta_vs_kpi_a_pp": round(
                float((bbs_h.get("full_30d") or {}).get("price_directional_hit_rate") or 0) - FROZEN_KPI_A,
                6,
            )
            * 100
            if (bbs_h.get("full_30d") or {}).get("price_directional_hit_rate")
            else None,
        },
        "metrics_180d_reference": {
            "existing_hybrid_180d_hit_rate": h180.get("hit_rate_all_rows"),
            "bbs_resolver_180d_overrides": 0,
            "note": "BBS pattern rare on 180d; prefer separate 180d hybrid lane for long panel.",
        },
        "gates": {
            "promotion_combined_all_passed": False,
            "human_review_required": True,
            "do_not_replace_frozen_kpi_a_headline": True,
        },
        "scripts": {
            "build_v6_resolver": "scripts/run_btrack_frozen30d_parallel_bundle_v6.py",
            "holdout7_panel": "scripts/run_btrack_frozen30d_parallel_bundle_v7.py",
        },
    }
    out = ROOT / "reports/btrack_bbs_ms_hybrid_candidate_manifest_v1_latest.json"
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"task": "bbs_candidate_manifest", "exit_code": 0, "report": str(out), "summary": manifest["metrics_frozen_30d_btc"]}


def _task_strategy_leaderboard_refresh() -> dict[str, Any]:
    comp_path = ROOT / "reports/btrack_prophecy_strategy_comparison_v1_latest.json"
    base = _load(comp_path) if comp_path.is_file() else {"schema": "btrack_prophecy_strategy_comparison_v1", "strategies": []}
    panel = _load(HOLDOUT7_PANEL) if HOLDOUT7_PANEL.is_file() else {}
    bbs = (panel.get("lanes") or {}).get("bbs_hybrid", {})

    new_rows = [
        {
            "id": "bbs_ms_hybrid_frozen30d",
            "label": "BBS resolver + MS hybrid (동결 30일)",
            "hit_rate_all_rows": (bbs.get("full_30d") or {}).get("price_directional_hit_rate"),
            "holdout7_hit_rate": (bbs.get("holdout7") or {}).get("price_directional_hit_rate"),
            "n_evaluated": (bbs.get("full_30d") or {}).get("n_evaluated"),
            "metric_kind": "price_directional_hit_rate",
            "source": "reports/btrack_frozen30d_holdout7_scored_panel_v1_latest.json",
            "promote_headline": False,
            "note": "Deployable resolver + MS; holdout7 ~43% not 60%.",
        },
        {
            "id": "bbs_solo_frozen30d",
            "label": "BBS resolver solo (동결 30일)",
            "hit_rate_all_rows": 0.6,
            "holdout7_hit_rate": 0.0,
            "n_evaluated": 30,
            "metric_kind": "price_directional_hit_rate",
            "source": "reports/btrack_frozen30d_holdout7_scored_panel_v1_latest.json",
            "promote_headline": False,
            "note": "Do not deploy without MS hybrid layer.",
        },
    ]
    strategies = [s for s in (base.get("strategies") or []) if s.get("id") not in {r["id"] for r in new_rows}]
    strategies.extend(new_rows)
    base["strategies"] = strategies
    base["generated_at_utc"] = _utc()
    base["research_only"] = True
    comp_path.write_text(json.dumps(base, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"task": "strategy_leaderboard_refresh", "exit_code": 0, "summary": {"added": [r["id"] for r in new_rows]}}


def _task_promotion_gates_bbs_hybrid_refresh() -> dict[str, Any]:
    if not BBS_HYBRID_PER.is_file():
        return {"task": "promotion_gates_bbs_hybrid", "exit_code": 2, "error": "missing bbs hybrid per_date"}
    gates_out = WORK / "promotion_gates_bbs_ms_hybrid.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(REC_CHAIN),
            "--recent-trading-days",
            "180",
            "--per-date-direction-json",
            str(BBS_HYBRID_PER.relative_to(ROOT)),
            "--gates-out",
            str(gates_out.relative_to(ROOT)),
            "--summary-out",
            str(WORK / "chain_summary_bbs_ms.json"),
            "--calibration-note",
            "bbs_ms_hybrid_candidate_v8",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    gates = _load(gates_out) if gates_out.is_file() else {}
    return {
        "task": "promotion_gates_bbs_hybrid",
        "exit_code": proc.returncode,
        "summary": {
            "combined_all_passed": bool(gates.get("combined_all_passed")),
            "outcome_class": gates.get("outcome_class"),
            "lens_wf_mean": next(
                (
                    (g.get("observed") or {}).get("mean_test_accuracy")
                    for g in (gates.get("tracks") or {}).get("per_date_lens", {}).get("gates") or []
                    if isinstance(g, dict) and g.get("gate_id") == "lens_wf_mean_test_accuracy"
                ),
                None,
            ),
        },
    }


def _task_train_miss_profile() -> dict[str, Any]:
    """Profile non-holdout misses on bbs hybrid (train 23d)."""
    if not HOLDOUT7_PANEL.is_file():
        return {"task": "train_miss_profile", "exit_code": 2, "error": "missing panel"}
    days = (_load(HOLDOUT7_PANEL).get("lanes") or {}).get("bbs_hybrid", {}).get("train23", {}).get("per_day") or []
    diff = _diff_map()
    misses = [d for d in days if isinstance(d, dict) and not d.get("hit")]
    profile: dict[str, int] = {}
    for m in misses:
        ed = str(m.get("eval_date") or "")[:10]
        d = diff.get(ed, {})
        act = str(m.get("actual") or "").lower()
        pred = str(m.get("pred") or "").lower()
        if act == "bull" and pred == "bear":
            key = "false_bear"
        elif act == "bear" and pred == "bull":
            key = "false_bull"
        else:
            key = "other"
        profile[key] = profile.get(key, 0) + 1

    out = ROOT / "reports/btrack_frozen30d_train23_miss_profile_v1_latest.json"
    out.write_text(
        json.dumps(
            {
                "schema": "btrack_frozen30d_train23_miss_profile_v1",
                "generated_at_utc": _utc(),
                "research_only": True,
                "n_miss": len(misses),
                "miss_breakdown": profile,
                "miss_dates": [str(m.get("eval_date"))[:10] for m in misses],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return {"task": "train_miss_profile", "exit_code": 0, "summary": {"n_miss": len(misses), **profile}}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    WORK.mkdir(parents=True, exist_ok=True)

    tasks = [
        _task_holdout7_miss_autopsy,
        _task_bbs_candidate_manifest,
        _task_strategy_leaderboard_refresh,
        _task_train_miss_profile,
        _task_promotion_gates_bbs_hybrid_refresh,
    ]
    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=5) as pool:
        futs = {pool.submit(fn): fn.__name__ for fn in tasks}
        for fut in as_completed(futs):
            try:
                results.append(fut.result())
            except Exception as exc:
                results.append({"task": futs[fut], "exit_code": 2, "error": str(exc)})

    bundle = {
        "schema": "btrack_frozen30d_parallel_bundle_v8",
        "generated_at_utc": _utc(),
        "research_only": True,
        "parallel_tasks": results,
    }
    args.output.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    for r in results:
        print(f"  {r.get('task')}: exit={r.get('exit_code')} {r.get('summary', r.get('error', ''))}")
    return 0 if all(int(r.get("exit_code", 1)) == 0 for r in results) else 2


if __name__ == "__main__":
    raise SystemExit(main())
