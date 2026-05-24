#!/usr/bin/env python3
"""[HYPO] Parallel bundle v7: holdout7 scored panel, prp-filter resolver, 180d hybrid gates."""
from __future__ import annotations

import argparse
import copy
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

DEFAULT_OUT = ROOT / "reports/btrack_frozen30d_parallel_bundle_v7_latest.json"
WORK = ROOT / "reports/btrack_frozen30d_parallel_bundle_v7_work"
V6_WORK = ROOT / "reports/btrack_frozen30d_parallel_bundle_v6_work"
ANCHOR_SCORE = ROOT / "reports/btrack_prophecy_score_30d_frozen_kpi_a_v1.json"
ANCHOR_DATES = ROOT / "reports/btrack_anchor_eval_dates_v1.json"
LEGACY_V1 = ROOT / "reports/btrack_ensemble_per_date_v1_prod_perdate_30d_v1.json"
M016_PER = ROOT / "reports/btrack_frozen30d_margin_fine_sweep_work/per_date_margin_016.json"
MS_PER = ROOT / "reports/btrack_lens_combo_ms_per_date_anchor_v1.json"
FEATURES = ROOT / "reports/btrack_wrong_dir_holdout_features_v1_latest.json"
DAILY_DIFF = ROOT / "reports/btrack_frozen30d_hybrid_daily_diff_v1_latest.json"
LEGACY_HYBRID_PER = ROOT / "reports/btrack_v1_ms_hybrid_work/agree_or_ms_else_v1/per_date.json"
BTC = ROOT / "research/market_data/btc_daily_external_yf.csv"
HYP = ROOT / "docs/final/artifacts/btrack_hypothesis_prophecy_latest.json"
REC_CHAIN = ROOT / "scripts/run_prophecy_btrack_recommended_eval_chain_v1.py"
BBS_HYBRID_PER = V6_WORK / "per_date_bull_bear_split_hybrid_hybrid.json"
if not BBS_HYBRID_PER.is_file():
    BBS_HYBRID_PER = V6_WORK / "per_date_bull_bear_split_hybrid.json"

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


def _anchor_dates() -> list[str]:
    if ANCHOR_DATES.is_file():
        dates = list(_load(ANCHOR_DATES).get("eval_dates") or [])
        if dates:
            return sorted(str(d)[:10] for d in dates)
    return sorted(_dir_map(_load(ANCHOR_SCORE)).keys())


def _run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)}\n{proc.stderr or proc.stdout}")


def _resolve_v1(
    legacy: str,
    m016: str,
    *,
    mode: str,
    feat: dict[str, Any] | None,
) -> str:
    if mode == "bull_bear_split":
        if legacy == "bull" and m016 == "bear":
            return legacy
        return m016
    if mode == "bull_bear_prp_low":
        if legacy == "bull" and m016 == "bear" and feat:
            prp = feat.get("prior_range_position")
            prp_f = float(prp) if prp is not None else 0.5
            if prp_f < 0.75:
                return legacy
        return m016
    if mode == "bull_bear_prp_low_070":
        if legacy == "bull" and m016 == "bear" and feat:
            prp = feat.get("prior_range_position")
            prp_f = float(prp) if prp is not None else 0.5
            if prp_f < 0.70:
                return legacy
        return m016
    raise ValueError(mode)


def _score_eval(per_date: Path, slug: str) -> tuple[dict[str, Any], Path]:
    sub = WORK / slug
    sub.mkdir(parents=True, exist_ok=True)
    dates_path = sub / "dates.json"
    dates_path.write_text(
        json.dumps({"eval_dates": _anchor_dates()}, indent=2) + "\n",
        encoding="utf-8",
    )
    score = sub / "score.json"
    ev = sub / "eval.json"
    lock = sub / ".score_writer.lock"
    py = sys.executable
    _run(
        [
            py,
            "scripts/build_btrack_prophecy_score_from_ohlcv.py",
            "--btc-csv",
            str(BTC.relative_to(ROOT)),
            "--hypothesis-json",
            str(HYP.relative_to(ROOT)),
            "--batch-eval-dates-json",
            str(dates_path.relative_to(ROOT)),
            "--per-date-direction-json",
            str(per_date.relative_to(ROOT)),
            "--lock-file",
            str(lock.relative_to(ROOT)),
            "--output",
            str(score.relative_to(ROOT)),
        ]
    )
    _run(
        [
            py,
            "scripts/eval_prophecy_hit_rate_v1.py",
            "--run-mode",
            "price",
            "--score-json",
            str(score.relative_to(ROOT)),
            "--headline-instrument",
            "btc",
            "--output",
            str(ev.relative_to(ROOT)),
        ]
    )
    return (_load(ev).get("metrics") or {}), score


def _slice_metrics(score_path: Path) -> dict[str, Any]:
    rows = [
        r
        for r in (_load(score_path).get("rows") or [])
        if isinstance(r, dict) and str(r.get("instrument") or "").lower() == "btc"
    ]

    def _agg(subset: list[str]) -> dict[str, Any]:
        h = n = 0
        days: list[dict[str, Any]] = []
        for r in rows:
            ed = str(r.get("eval_date") or "")[:10]
            if ed not in subset:
                continue
            pred = str(r.get("predicted_direction") or "").lower()
            act = str(r.get("actual_direction") or "").lower()
            if pred not in ("bull", "bear") or act not in ("bull", "bear"):
                continue
            n += 1
            hit = pred == act
            if hit:
                h += 1
            days.append({"eval_date": ed, "pred": pred, "actual": act, "hit": hit})
        return {
            "n_evaluated": n,
            "price_hits": h,
            "price_directional_hit_rate": round(h / n, 6) if n else None,
            "per_day": days,
        }

    all_dates = {str(r.get("eval_date") or "")[:10] for r in rows}
    h7 = _agg(sorted(HOLDOUT7))
    train = _agg(sorted(all_dates - HOLDOUT7))
    full = _agg(all_dates)
    return {"full_30d": full, "holdout7": h7, "train23": train}


def _task_holdout7_panel() -> dict[str, Any]:
    lanes: dict[str, Path] = {
        "m016_solo": M016_PER,
        "bbs_solo": V6_WORK / "per_date_bull_bear_split.json",
        "bbs_hybrid": BBS_HYBRID_PER,
        "legacy_hybrid": LEGACY_HYBRID_PER,
        "disagree_legacy": V6_WORK / "per_date_disagree_use_legacy.json",
    }
    missing = [k for k, p in lanes.items() if not p.is_file()]
    if missing:
        return {"task": "holdout7_panel", "exit_code": 2, "error": f"missing lanes: {missing}"}

    summary: dict[str, Any] = {}

    def _one(name: str, per: Path) -> tuple[str, dict[str, Any]]:
        metrics, score = _score_eval(per, f"holdout7_{name}")
        sliced = _slice_metrics(score)
        return name, {"pipeline_metrics": metrics, **sliced}

    with ThreadPoolExecutor(max_workers=5) as pool:
        futs = {pool.submit(_one, n, p): n for n, p in lanes.items()}
        for fut in as_completed(futs):
            name, data = fut.result()
            summary[name] = data

    out = ROOT / "reports/btrack_frozen30d_holdout7_scored_panel_v1_latest.json"
    report = {
        "schema": "btrack_frozen30d_holdout7_scored_panel_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "holdout7_dates": sorted(HOLDOUT7),
        "lanes": summary,
        "insight": "Compare solo bbs (expected weak on H7) vs bbs+MS hybrid vs legacy hybrid.",
    }
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"task": "holdout7_panel", "exit_code": 0, "report": str(out), "summary": summary}


def _task_prp_simulation() -> dict[str, Any]:
    feat_by: dict[str, dict[str, Any]] = {}
    if FEATURES.is_file():
        for row in _load(FEATURES).get("rows") or []:
            if isinstance(row, dict):
                ed = str(row.get("eval_date") or "")[:10]
                if ed:
                    feat_by[ed] = row

    modes = ("bull_bear_split", "bull_bear_prp_low", "bull_bear_prp_low_070")
    rules: dict[str, Any] = {}
    for mode in modes:
        bucket = {"full": [0, 0], "h7": [0, 0], "train": [0, 0]}
        overrides: list[str] = []
        for day in _load(DAILY_DIFF).get("per_day") or []:
            if not isinstance(day, dict):
                continue
            ed = str(day.get("eval_date") or "")[:10]
            act = str(day.get("actual") or "").lower()
            leg = str(day.get("legacy_v1") or "").lower()
            m16 = str(day.get("m016_v1") or "").lower()
            pred = _resolve_v1(leg, m16, mode=mode, feat=feat_by.get(ed))
            if leg == "bull" and m16 == "bear" and pred == leg:
                overrides.append(ed)
            if pred not in ("bull", "bear") or act not in ("bull", "bear"):
                continue
            hit = int(pred == act)
            bucket["full"][0] += hit
            bucket["full"][1] += 1
            key = "h7" if ed in HOLDOUT7 else "train"
            bucket[key][0] += hit
            bucket[key][1] += 1
        rules[mode] = {
            "override_dates": overrides,
            "full_30d": _rate(bucket["full"]),
            "holdout7": _rate(bucket["h7"]),
            "train23": _rate(bucket["train"]),
        }

    out = ROOT / "reports/btrack_frozen30d_prp_filter_sim_v1_latest.json"
    out.write_text(
        json.dumps(
            {
                "schema": "btrack_frozen30d_prp_filter_sim_v1",
                "generated_at_utc": _utc(),
                "research_only": True,
                "rules": rules,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return {"task": "prp_simulation", "exit_code": 0, "report": str(out), "summary": rules}


def _rate(pair: list[int]) -> dict[str, Any]:
    h, n = pair
    return {"price_hits": h, "n_evaluated": n, "price_directional_hit_rate": round(h / n, 6) if n else None}


def _build_prp_per_date(mode: str, out: Path) -> dict[str, Any]:
    feat_by: dict[str, dict[str, Any]] = {}
    if FEATURES.is_file():
        for row in _load(FEATURES).get("rows") or []:
            if isinstance(row, dict):
                ed = str(row.get("eval_date") or "")[:10]
                if ed:
                    feat_by[ed] = row
    legacy_map = _dir_map(_load(LEGACY_V1))
    m016_doc = _load(M016_PER)
    m016_map = _dir_map(m016_doc)
    n_ov = 0
    rows: list[dict[str, Any]] = []
    for row in m016_doc.get("rows") or []:
        if not isinstance(row, dict):
            continue
        r = copy.deepcopy(row)
        ed = str(r.get("eval_date") or "")[:10]
        leg = legacy_map.get(ed, "neutral")
        m16 = m016_map.get(ed, "neutral")
        pred = _resolve_v1(leg, m16, mode=mode, feat=feat_by.get(ed))
        if pred != m16:
            n_ov += 1
        r["predicted_direction"] = pred
        rows.append(r)
    doc = copy.deepcopy(m016_doc)
    doc["rows"] = rows
    doc["v1_resolver_meta"] = {"mode": mode, "n_overrides": n_ov}
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"mode": mode, "n_overrides": n_ov}


def _task_pipeline_prp_low() -> dict[str, Any]:
    per = WORK / "per_date_bull_bear_prp_low.json"
    meta = _build_prp_per_date("bull_bear_prp_low", per)
    metrics, _ = _score_eval(per, "bull_bear_prp_low")
    return {"task": "pipeline_prp_low", "exit_code": 0, "summary": {**meta, **metrics}}


def _task_disagree_legacy_score() -> dict[str, Any]:
    per = V6_WORK / "per_date_disagree_use_legacy.json"
    if not per.is_file():
        return {"task": "disagree_legacy_score", "exit_code": 2, "error": "missing per_date"}
    metrics, _ = _score_eval(per, "disagree_use_legacy_retry")
    return {"task": "disagree_legacy_score", "exit_code": 0, "summary": metrics}


def _task_bbs_hybrid_180d_gates() -> dict[str, Any]:
    """Apply bull_bear_split on 180d legacy(prod) + freshly built m016 180d, then hybrid+gates."""
    from scripts.run_btrack_frozen30d_margin_penalty_grid_v1 import (
        _apply_cfg,
        _load as mg_load,
        _run as mg_run,
    )

    legacy180 = ROOT / "reports/btrack_ensemble_per_date_directions_180d_v1.json"
    if not legacy180.is_file():
        legacy180 = ROOT / "reports/btrack_ensemble_per_date_directions_180d_v1_latest.json"
    base_cfg = mg_load(ROOT / "docs/final/artifacts/btrack_lens_ensemble_v1.json")
    m016_cfg = _apply_cfg(base_cfg, {"slug": "margin_016", "tie_break_min_margin": 0.016})
    work = WORK / "margin_016_180d"
    work.mkdir(parents=True, exist_ok=True)
    cfg_path = work / "ens_margin_016.json"
    m016_180 = work / "per_date_margin_016.json"
    cfg_path.write_text(json.dumps(m016_cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if not m016_180.is_file():
        score180 = ROOT / "reports/btrack_promotion_push_work/sweep_180d/nbps_0_4/score_v1_180d.json"
        if not score180.is_file():
            return {
                "task": "bbs_hybrid_180d_gates",
                "exit_code": 2,
                "error": "missing 180d score anchor for ensemble build",
            }
        py = sys.executable
        mg_run(
            [
                py,
                "scripts/build_btrack_ensemble_per_date_directions_v1.py",
                "--score-json",
                str(score180.relative_to(ROOT)),
                "--ensemble-config",
                str(cfg_path.relative_to(ROOT)),
                "--ensemble-mode",
                "v1",
                "--output",
                str(m016_180.relative_to(ROOT)),
            ]
        )

    legacy_map = _dir_map(_load(legacy180))
    m016_map = _dir_map(_load(m016_180))
    dates = sorted(set(legacy_map) & set(m016_map))
    resolved: dict[str, str] = {}
    for ed in dates:
        leg, m16 = legacy_map[ed], m016_map[ed]
        resolved[ed] = leg if leg == "bull" and m16 == "bear" else m16

    from scripts.run_btrack_v1_ms_hybrid_parallel_v1 import (
        _merge_agree_or_ms_else_v1,
        build_hybrid_rows,
        MS_PER_DATE,
    )

    ms_path = ROOT / "reports/btrack_ms_180d_expansion_work/ms_per_date_180d.json"
    if not ms_path.is_file():
        ms_path = MS_PER
    ms_map = _dir_map(_load(ms_path))
    per_h = work / "hybrid_bbs_180d.json"
    doc = {
        "schema": "btrack_ensemble_per_date_directions_v1",
        "version": "1.0.0",
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "ts_utc": _utc(),
        "ensemble_mode": "hybrid_bbs_180d",
        "research_only": True,
        "rows": build_hybrid_rows(
            dates=dates,
            v1_map=resolved,
            ms_map=ms_map,
            rule_id="agree_or_ms_else_v1",
            merge_fn=_merge_agree_or_ms_else_v1,
        ),
    }
    per_h.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    from scripts.run_btrack_wrong_dir_holdout_v1 import _pipeline_eval

    ev = _pipeline_eval(per_h, 180)
    m = ev.get("metrics") or {}
    gates_out = work / "promotion_gates_bbs_hybrid_180d.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(REC_CHAIN),
            "--recent-trading-days",
            "180",
            "--per-date-direction-json",
            str(per_h.relative_to(ROOT)),
            "--gates-out",
            str(gates_out.relative_to(ROOT)),
            "--summary-out",
            str(work / "chain_summary.json"),
            "--calibration-note",
            "bbs_hybrid_180d_v7",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    gates = _load(gates_out) if gates_out.is_file() else {}
    return {
        "task": "bbs_hybrid_180d_gates",
        "exit_code": proc.returncode,
        "summary": {
            "headline_180d": m.get("price_directional_hit_rate"),
            "n_evaluated": m.get("n_evaluated"),
            "combined_all_passed": bool(gates.get("combined_all_passed")),
            "outcome_class": gates.get("outcome_class"),
            "n_resolver_dates": len(dates),
            "n_overrides": sum(1 for ed in dates if resolved[ed] != m016_map[ed]),
        },
        "stderr_tail": (proc.stderr or "")[-500:] if proc.returncode else None,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    WORK.mkdir(parents=True, exist_ok=True)

    results: list[dict[str, Any]] = []

    with ThreadPoolExecutor(max_workers=4) as pool:
        futs = [
            pool.submit(_task_prp_simulation),
            pool.submit(_task_disagree_legacy_score),
            pool.submit(_task_pipeline_prp_low),
            pool.submit(_task_bbs_hybrid_180d_gates),
        ]
        for fut in as_completed(futs):
            try:
                results.append(fut.result())
            except Exception as exc:
                results.append({"task": "parallel", "exit_code": 2, "error": str(exc)})

    # holdout7 panel is heavy (5 score runs) — run after or in parallel; run sequentially to avoid lock
    try:
        results.append(_task_holdout7_panel())
    except Exception as exc:
        results.append({"task": "holdout7_panel", "exit_code": 2, "error": str(exc)})

    bundle = {
        "schema": "btrack_frozen30d_parallel_bundle_v7",
        "generated_at_utc": _utc(),
        "research_only": True,
        "track_a_auto_promote": False,
        "parallel_tasks": results,
    }
    args.output.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    for r in results:
        print(f"  {r.get('task')}: exit={r.get('exit_code')} {r.get('summary', r.get('error', ''))}")
    return 0 if all(int(r.get("exit_code", 1)) == 0 for r in results) else 2


if __name__ == "__main__":
    raise SystemExit(main())
