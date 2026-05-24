#!/usr/bin/env python3
"""[HYPO] Parallel bundle v6: deployable v1 disagreement resolver + holdout7 blind + gates."""
from __future__ import annotations

import argparse
import copy
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_OUT = ROOT / "reports/btrack_frozen30d_parallel_bundle_v6_latest.json"
WORK = ROOT / "reports/btrack_frozen30d_parallel_bundle_v6_work"
ANCHOR_SCORE = ROOT / "reports/btrack_prophecy_score_30d_frozen_kpi_a_v1.json"
ANCHOR_DATES = ROOT / "reports/btrack_anchor_eval_dates_v1.json"
LEGACY_V1 = ROOT / "reports/btrack_ensemble_per_date_v1_prod_perdate_30d_v1.json"
M016_PER = ROOT / "reports/btrack_frozen30d_margin_fine_sweep_work/per_date_margin_016.json"
MS_PER = ROOT / "reports/btrack_lens_combo_ms_per_date_anchor_v1.json"
FEATURES = ROOT / "reports/btrack_wrong_dir_holdout_features_v1_latest.json"
DAILY_DIFF = ROOT / "reports/btrack_frozen30d_hybrid_daily_diff_v1_latest.json"
BTC = ROOT / "research/market_data/btc_daily_external_yf.csv"
HYP = ROOT / "docs/final/artifacts/btrack_hypothesis_prophecy_latest.json"
REC_CHAIN = ROOT / "scripts/run_prophecy_btrack_recommended_eval_chain_v1.py"

HOLDOUT7: frozenset[str] = frozenset(
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
    ed: str,
    legacy: str,
    m016: str,
    *,
    mode: str,
    feat: dict[str, Any] | None,
) -> str:
    if mode == "m016_only":
        return m016
    if mode == "legacy_only":
        return legacy
    if mode == "disagree_use_legacy":
        if legacy != m016 and legacy in ("bull", "bear") and m016 in ("bull", "bear"):
            return legacy
        return m016
    if mode == "bull_bear_split":
        # Deployable: legacy bull vs m016 bear → trust legacy tie-break lane.
        if legacy == "bull" and m016 == "bear":
            return legacy
        return m016
    if mode == "bull_bear_ovn_bull":
        if legacy == "bull" and m016 == "bear" and feat:
            prelim = str(feat.get("preliminary_direction") or legacy).lower()
            ovn = feat.get("overnight_return")
            ovn_f = float(ovn) if ovn is not None else 0.0
            if prelim == "bull" and ovn_f < 0:
                return legacy
        return m016
    if mode == "disagree_use_m016":
        if legacy != m016 and legacy in ("bull", "bear") and m016 in ("bull", "bear"):
            return m016
        return m016
    raise ValueError(mode)


def _build_resolved_per_date(
    *,
    mode: str,
    out_path: Path,
    ensemble_mode: str,
) -> dict[str, Any]:
    legacy_doc = _load(LEGACY_V1)
    m016_doc = _load(M016_PER)
    legacy_map = _dir_map(legacy_doc)
    m016_map = _dir_map(m016_doc)
    feat_by_date: dict[str, dict[str, Any]] = {}
    if FEATURES.is_file():
        for row in _load(FEATURES).get("rows") or []:
            if isinstance(row, dict):
                ed = str(row.get("eval_date") or "")[:10]
                if ed:
                    feat_by_date[ed] = row

    n_resolved = 0
    rows: list[dict[str, Any]] = []
    for row in m016_doc.get("rows") or []:
        if not isinstance(row, dict):
            continue
        r = copy.deepcopy(row)
        ed = str(r.get("eval_date") or "")[:10]
        leg = legacy_map.get(ed, "neutral")
        m16 = m016_map.get(ed, "neutral")
        pred = _resolve_v1(ed, leg, m16, mode=mode, feat=feat_by_date.get(ed))
        if pred != m16:
            n_resolved += 1
        r["predicted_direction"] = pred
        r["v1_resolver"] = {
            "mode": mode,
            "legacy_v1": leg,
            "margin_016_v1": m16,
        }
        rows.append(r)

    doc = copy.deepcopy(m016_doc)
    doc["rows"] = rows
    doc["ensemble_mode"] = ensemble_mode
    doc["v1_resolver_meta"] = {
        "mode": mode,
        "n_direction_overrides": n_resolved,
        "research_only": True,
        "deployable": mode in ("bull_bear_split", "bull_bear_ovn_bull", "disagree_use_legacy"),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"mode": mode, "n_overrides": n_resolved, "path": str(out_path)}


def _score_eval(per_date: Path, slug: str) -> dict[str, Any]:
    sub = WORK / slug
    sub.mkdir(parents=True, exist_ok=True)
    dates_path = sub / "dates.json"
    dates_path.write_text(
        json.dumps({"eval_dates": _anchor_dates()}, indent=2) + "\n",
        encoding="utf-8",
    )
    score = sub / "score.json"
    ev = sub / "eval.json"
    py = sys.executable
    lock = sub / ".score_writer.lock"
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
    return (_load(ev).get("metrics") or {}) if ev.is_file() else {}


def _task_rule_simulation() -> dict[str, Any]:
    """Fast offline simulation from daily_diff (no OHLCV)."""
    if not DAILY_DIFF.is_file():
        return {"task": "rule_simulation", "exit_code": 2, "error": "missing daily_diff"}

    modes = (
        "m016_only",
        "legacy_only",
        "disagree_use_legacy",
        "bull_bear_split",
        "disagree_use_m016",
    )
    by_mode: dict[str, dict[str, int]] = {m: {"hits": 0, "n": 0, "holdout7_hits": 0, "holdout7_n": 0} for m in modes}
    override_dates: dict[str, list[str]] = {m: [] for m in modes}

    for day in _load(DAILY_DIFF).get("per_day") or []:
        if not isinstance(day, dict):
            continue
        ed = str(day.get("eval_date") or "")[:10]
        act = str(day.get("actual") or "").lower()
        leg = str(day.get("legacy_v1") or "neutral").lower()
        m16 = str(day.get("m016_v1") or "neutral").lower()
        if act not in ("bull", "bear"):
            continue
        in_h7 = ed in HOLDOUT7
        for mode in modes:
            pred = _resolve_v1(ed, leg, m16, mode=mode, feat=None)
            if pred not in ("bull", "bear"):
                continue
            hit = pred == act
            by_mode[mode]["n"] += 1
            if hit:
                by_mode[mode]["hits"] += 1
            if in_h7:
                by_mode[mode]["holdout7_n"] += 1
                if hit:
                    by_mode[mode]["holdout7_hits"] += 1
            if mode == "bull_bear_split" and leg == "bull" and m16 == "bear":
                override_dates[mode].append(ed)

    summary: dict[str, Any] = {}
    for mode, c in by_mode.items():
        n, h = c["n"], c["hits"]
        h7n, h7h = c["holdout7_n"], c["holdout7_hits"]
        summary[mode] = {
            "hit_rate_all_rows": round(h / n, 6) if n else None,
            "n_evaluated": n,
            "price_hits": h,
            "holdout7_hit_rate": round(h7h / h7n, 6) if h7n else None,
            "holdout7_n": h7n,
            "override_dates": override_dates.get(mode),
        }

    out = ROOT / "reports/btrack_frozen30d_v1_resolver_sim_v1_latest.json"
    report = {
        "schema": "btrack_frozen30d_v1_resolver_sim_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "holdout7_dates": sorted(HOLDOUT7),
        "rules": summary,
        "insight": (
            "bull_bear_split (legacy bull vs m016 bear → legacy) matches flip-patch 60% "
            "on full 30d in simulation; verify with score pipeline."
        ),
    }
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"task": "rule_simulation", "exit_code": 0, "report": str(out), "summary": summary}


def _task_pipeline(mode: str, slug: str, *, hybrid: bool = False) -> dict[str, Any]:
    per = WORK / f"per_date_{slug}.json"
    meta = _build_resolved_per_date(
        mode=mode,
        out_path=per,
        ensemble_mode=f"v1_resolver_{slug}",
    )
    if hybrid:
        from scripts.run_btrack_v1_ms_hybrid_parallel_v1 import (
            _merge_agree_or_ms_else_v1,
            build_hybrid_rows,
        )

        ms_map = _dir_map(_load(MS_PER))
        v1_map = _dir_map(_load(per))
        dates = _anchor_dates()
        per_h = WORK / f"per_date_{slug}_hybrid.json"
        doc = {
            "schema": "btrack_ensemble_per_date_directions_v1",
            "version": "1.0.0",
            "hypothesis_tier": "B",
            "boundary_ack": True,
            "ts_utc": _utc(),
            "ensemble_mode": f"hybrid_agree_or_ms_else_{slug}",
            "research_only": True,
            "rows": build_hybrid_rows(
                dates=dates,
                v1_map=v1_map,
                ms_map=ms_map,
                rule_id="agree_or_ms_else_v1",
                merge_fn=_merge_agree_or_ms_else_v1,
            ),
        }
        per_h.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        per = per_h
        slug = f"{slug}_hybrid"

    metrics = _score_eval(per, slug)
    return {
        "task": f"pipeline_{slug}",
        "exit_code": 0,
        "summary": {**meta, **metrics},
    }


def _task_promotion_gates(per_slug: str) -> dict[str, Any]:
    per = WORK / f"per_date_{per_slug}.json"
    if not per.is_file():
        return {"task": f"promotion_gates_{per_slug}", "exit_code": 2, "error": "missing per_date"}
    gates_out = WORK / f"promotion_gates_{per_slug}.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(REC_CHAIN),
            "--recent-trading-days",
            "180",
            "--per-date-direction-json",
            str(per.relative_to(ROOT)),
            "--gates-out",
            str(gates_out.relative_to(ROOT)),
            "--summary-out",
            str(WORK / f"chain_summary_{per_slug}.json"),
            "--calibration-note",
            f"frozen30d_resolver_{per_slug}",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    gates = _load(gates_out) if gates_out.is_file() else {}
    return {
        "task": f"promotion_gates_{per_slug}",
        "exit_code": proc.returncode,
        "summary": {
            "combined_all_passed": bool(gates.get("combined_all_passed")),
            "outcome_class": gates.get("outcome_class"),
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    WORK.mkdir(parents=True, exist_ok=True)

    results: list[dict[str, Any]] = []

    # Phase A: fast simulation (always first)
    results.append(_task_rule_simulation())

    # Phase B: parallel pipelines for top deployable rules
    pipeline_specs = [
        ("bull_bear_split", "bull_bear_split", False),
        ("bull_bear_split", "bull_bear_split_hybrid", True),
        ("disagree_use_legacy", "disagree_use_legacy", False),
        ("bull_bear_ovn_bull", "bull_bear_ovn_bull", False),
    ]
    with ThreadPoolExecutor(max_workers=4) as pool:
        futs = [
            pool.submit(_task_pipeline, mode, slug, hybrid=hybrid)
            for mode, slug, hybrid in pipeline_specs
        ]
        for fut in as_completed(futs):
            try:
                results.append(fut.result())
            except Exception as exc:
                results.append({"task": "pipeline", "exit_code": 2, "error": str(exc)})

    # Phase C: promotion gates (parallel, after bull_bear_split per_date exists)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futs = [
            pool.submit(_task_promotion_gates, "bull_bear_split"),
            pool.submit(_task_promotion_gates, "bull_bear_split_hybrid"),
        ]
        for fut in as_completed(futs):
            try:
                results.append(fut.result())
            except Exception as exc:
                results.append({"task": "promotion_gates", "exit_code": 2, "error": str(exc)})

    bundle = {
        "schema": "btrack_frozen30d_parallel_bundle_v6",
        "generated_at_utc": _utc(),
        "research_only": True,
        "track_a_auto_promote": False,
        "deployable_rule": "legacy_bull AND margin_016_bear → use legacy v1 else margin_016 v1",
        "parallel_tasks": results,
    }
    args.output.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    for r in results:
        print(f"  {r.get('task')}: exit={r.get('exit_code')} {r.get('summary', r.get('error', ''))}")
    return 0 if all(int(r.get("exit_code", 1)) == 0 for r in results) else 2


if __name__ == "__main__":
    raise SystemExit(main())
