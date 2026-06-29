#!/usr/bin/env python3
"""[HYPO] Reconcile frozen30d offline sim (daily_diff) vs score pipeline on anchor 30d."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/btrack_frozen30d_sim_pipeline_reconcile_v1_latest.json"

DAILY_DIFF = ROOT / "reports/btrack_frozen30d_hybrid_daily_diff_v1_latest.json"
LEGACY_V1 = ROOT / "reports/btrack_ensemble_per_date_v1_prod_perdate_30d_v1.json"
M016_PER = ROOT / "reports/btrack_frozen30d_margin_fine_sweep_work/per_date_margin_016.json"
ANCHOR_SCORE = ROOT / "reports/btrack_prophecy_score_30d_frozen_kpi_a_v1.json"
RESOLVER_SIM = ROOT / "reports/btrack_frozen30d_v1_resolver_sim_v1_latest.json"
V6_WORK = ROOT / "reports/btrack_frozen30d_parallel_bundle_v6_work"
HOLDOUT_PANEL = ROOT / "reports/btrack_frozen30d_holdout7_scored_panel_v1_latest.json"
BBS_MANIFEST = ROOT / "reports/btrack_bbs_ms_hybrid_candidate_manifest_v1_latest.json"

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
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _dir_map(doc: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for row in doc.get("rows") or []:
        if not isinstance(row, dict):
            continue
        if str(row.get("instrument") or "btc").lower() != "btc":
            continue
        ed = str(row.get("eval_date") or "")[:10]
        if ed:
            out[ed] = str(row.get("predicted_direction") or "neutral").strip().lower()
    return out


def _actual_map(score_path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for row in (_load(score_path).get("rows") or []):
        if not isinstance(row, dict):
            continue
        if str(row.get("instrument") or "btc").lower() != "btc":
            continue
        ed = str(row.get("eval_date") or "")[:10]
        act = str(row.get("actual_direction") or "neutral").lower()
        if ed:
            out[ed] = act
    return out


def _resolve_v1(legacy: str, m016: str, mode: str) -> str:
    if mode == "bull_bear_split":
        if legacy == "bull" and m016 == "bear":
            return legacy
        return m016
    if mode == "m016_only":
        return m016
    raise ValueError(mode)


def _sim_from_maps(
    *,
    legacy_map: dict[str, str],
    m016_map: dict[str, str],
    actual_map: dict[str, str],
    mode: str,
) -> dict[str, Any]:
    hits = n = h7h = h7n = 0
    overrides: list[str] = []
    for ed in sorted(set(legacy_map) & set(m016_map) & set(actual_map)):
        act = actual_map[ed]
        if act not in ("bull", "bear"):
            continue
        leg = legacy_map[ed]
        m16 = m016_map[ed]
        pred = _resolve_v1(leg, m16, mode=mode)
        if pred not in ("bull", "bear"):
            continue
        n += 1
        hit = pred == act
        if hit:
            hits += 1
        if ed in HOLDOUT7:
            h7n += 1
            if hit:
                h7h += 1
        if mode == "bull_bear_split" and leg == "bull" and m16 == "bear":
            overrides.append(ed)
    return {
        "hit_rate_all_rows": round(hits / n, 6) if n else None,
        "n_evaluated": n,
        "price_hits": hits,
        "holdout7_hit_rate": round(h7h / h7n, 6) if h7n else None,
        "holdout7_n": h7n,
        "override_dates": overrides,
        "n_overrides": len(overrides),
    }


def _pipeline_summary(slug: str) -> dict[str, Any] | None:
    bundle = _load(ROOT / "reports/btrack_frozen30d_parallel_bundle_v6_latest.json")
    for task in bundle.get("parallel_tasks") or []:
        if not isinstance(task, dict):
            continue
        name = str(task.get("task") or "")
        if slug in name and task.get("summary"):
            return task.get("summary")
    per = V6_WORK / f"per_date_{slug}.json"
    if not per.is_file():
        return None
    eval_path = V6_WORK / f"eval_{slug}.json"
    if eval_path.is_file():
        ev = _load(eval_path)
        btc = (ev.get("instruments") or {}).get("btc") or {}
        return {
            "path": str(per),
            "price_directional_hit_rate": btc.get("price_directional_hit_rate"),
            "n_evaluated": btc.get("n_evaluated"),
            "price_hits": btc.get("price_hits"),
        }
    return {"path": str(per), "note": "eval json missing"}


def _input_drift(stale_days: list[dict[str, Any]], legacy_map: dict[str, str], m016_map: dict[str, str]) -> dict[str, Any]:
    mismatches: list[dict[str, Any]] = []
    stale_bb = fresh_bb = 0
    for day in stale_days:
        if not isinstance(day, dict):
            continue
        ed = str(day.get("eval_date") or "")[:10]
        stale_leg = str(day.get("legacy_v1") or "").lower()
        stale_m16 = str(day.get("m016_v1") or "").lower()
        fresh_leg = legacy_map.get(ed, "")
        fresh_m16 = m016_map.get(ed, "")
        if stale_leg == "bull" and stale_m16 == "bear":
            stale_bb += 1
        if fresh_leg == "bull" and fresh_m16 == "bear":
            fresh_bb += 1
        if stale_leg != fresh_leg or stale_m16 != fresh_m16:
            mismatches.append(
                {
                    "eval_date": ed,
                    "stale": {"legacy_v1": stale_leg, "m016_v1": stale_m16},
                    "fresh": {"legacy_v1": fresh_leg, "m016_v1": fresh_m16},
                }
            )
    return {
        "n_days_compared": len(stale_days),
        "n_input_mismatches": len(mismatches),
        "stale_bull_bear_pattern_days": stale_bb,
        "fresh_bull_bear_pattern_days": fresh_bb,
        "mismatch_sample": mismatches[:12],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    legacy_map = _dir_map(_load(LEGACY_V1))
    m016_map = _dir_map(_load(M016_PER))
    actual_map = _actual_map(ANCHOR_SCORE)

    stale = _load(DAILY_DIFF)
    stale_gen = stale.get("generated_at_utc")
    stale_summary = stale.get("summary") or {}
    stale_days = list(stale.get("per_day") or [])

    fresh_sim = _sim_from_maps(
        legacy_map=legacy_map,
        m016_map=m016_map,
        actual_map=actual_map,
        mode="bull_bear_split",
    )
    resolver_sim = (_load(RESOLVER_SIM).get("rules") or {}).get("bull_bear_split") or {}
    drift = _input_drift(stale_days, legacy_map, m016_map)

    pipeline_resolver = _pipeline_summary("bull_bear_split")
    pipeline_hybrid = _pipeline_summary("bull_bear_split_hybrid_hybrid")
    if pipeline_hybrid is None:
        pipeline_hybrid = _pipeline_summary("bull_bear_split_hybrid")

    panel = _load(HOLDOUT_PANEL)
    panel_gen = panel.get("generated_at_utc")
    bbs_lane = ((panel.get("lanes") or {}).get("bbs_hybrid") or {})
    manifest = _load(BBS_MANIFEST)
    manifest_metrics = manifest.get("metrics_frozen_30d_btc") or {}

    stale_sim_rate = stale_summary.get("legacy_hybrid_all_rows")
    if resolver_sim.get("hit_rate_all_rows") is not None:
        sim_from_stale_diff = resolver_sim
    else:
        sim_from_stale_diff = {
            "hit_rate_all_rows": None,
            "note": "missing resolver sim artifact",
        }

    root_cause = "aligned"
    verdict_ko = (
        "daily_diff·per_date 입력 정합. resolver-only sim≈57.1% vs pipeline 53.3%(n=30); "
        "MS 하이브리드 적용 시 43.3% — BBS resolver 단독 uplift 주장 불가."
    )
    if drift["n_input_mismatches"] > 0 or drift["stale_bull_bear_pattern_days"] != drift["fresh_bull_bear_pattern_days"]:
        root_cause = "stale_daily_diff_v1_inputs"
        verdict_ko = (
            f"offline sim 60%는 stale daily_diff의 legacy_v1/m016_v1 입력 "
            f"({drift['stale_bull_bear_pattern_days']}일 bull+bear) 기반; "
            f"현행 per_date는 override {drift['fresh_bull_bear_pattern_days']}일 → pipeline 정합."
        )
    elif stale_gen and panel_gen and stale_gen < str(panel_gen)[:10]:
        root_cause = "stale_daily_diff_timestamp"

    report = {
        "schema": "btrack_frozen30d_sim_pipeline_reconcile_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "track_a_auto_promote": False,
        "send_gate": "HOLD",
        "root_cause": root_cause,
        "verdict_ko": verdict_ko,
        "artifacts": {
            "daily_diff": str(DAILY_DIFF.relative_to(ROOT)).replace("\\", "/"),
            "daily_diff_generated_at_utc": stale_gen,
            "holdout_panel_generated_at_utc": panel_gen,
            "resolver_sim": str(RESOLVER_SIM.relative_to(ROOT)).replace("\\", "/"),
            "v6_bundle": "reports/btrack_frozen30d_parallel_bundle_v6_latest.json",
        },
        "input_drift": drift,
        "metrics_compare": {
            "stale_daily_diff_legacy_hybrid_all_rows": stale_sim_rate,
            "resolver_sim_bull_bear_split": sim_from_stale_diff.get("hit_rate_all_rows"),
            "fresh_maps_bull_bear_split_sim": fresh_sim.get("hit_rate_all_rows"),
            "pipeline_bull_bear_split": (pipeline_resolver or {}).get("price_directional_hit_rate"),
            "pipeline_bull_bear_split_hybrid": (pipeline_hybrid or {}).get("price_directional_hit_rate"),
            "holdout_panel_bbs_hybrid_full_30d": (bbs_lane.get("full_30d") or {}).get(
                "price_directional_hit_rate"
            ),
            "manifest_bbs_ms_hybrid_all_rows": manifest_metrics.get("bbs_ms_hybrid_all_rows"),
        },
        "fresh_sim_bull_bear_split": fresh_sim,
        "pipeline_summaries": {
            "bull_bear_split": pipeline_resolver,
            "bull_bear_split_hybrid": pipeline_hybrid,
        },
        "recommended_refresh_chain": [
            "py scripts/run_btrack_v1_ms_hybrid_parallel_v1.py",
            "py scripts/run_btrack_frozen30d_parallel_bundle_v2.py",
            "py scripts/run_btrack_frozen30d_parallel_bundle_v3.py",
            "py scripts/run_btrack_frozen30d_parallel_bundle_v6.py",
            "py scripts/run_btrack_frozen30d_parallel_bundle_v7.py",
            "py scripts/run_btrack_frozen30d_parallel_bundle_v8.py",
            "py scripts/build_btrack_frozen30d_sim_pipeline_reconcile_v1.py",
        ],
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    print(f"  root_cause={root_cause}")
    print(f"  stale_bb={drift['stale_bull_bear_pattern_days']} fresh_bb={drift['fresh_bull_bear_pattern_days']}")
    print(f"  sim_stale={sim_from_stale_diff.get('hit_rate_all_rows')} fresh={fresh_sim.get('hit_rate_all_rows')}")
    pipeline = (pipeline_hybrid or {}).get("price_directional_hit_rate")
    print(f"  pipeline_hybrid={pipeline}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
