#!/usr/bin/env python3
"""[HYPO] Parallel bundle v5: flip-patch counterfactual, rolling holdout, force-neutral probes."""
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

DEFAULT_OUT = ROOT / "reports/btrack_frozen30d_parallel_bundle_v5_latest.json"
WORK = ROOT / "reports/btrack_frozen30d_parallel_bundle_v5_work"
ANCHOR_SCORE = ROOT / "reports/btrack_prophecy_score_30d_frozen_kpi_a_v1.json"
ANCHOR_DATES = ROOT / "reports/btrack_anchor_eval_dates_v1.json"
LEGACY_V1 = ROOT / "reports/btrack_ensemble_per_date_v1_prod_perdate_30d_v1.json"
M016_PER = ROOT / "reports/btrack_frozen30d_margin_fine_sweep_work/per_date_margin_016.json"
MS_PER = ROOT / "reports/btrack_lens_combo_ms_per_date_anchor_v1.json"
BTC = ROOT / "research/market_data/btc_daily_external_yf.csv"
HYP = ROOT / "docs/final/artifacts/btrack_hypothesis_prophecy_latest.json"
FLIP_DATES = ("2026-04-30", "2026-05-14")
REC_CHAIN = ROOT / "scripts/run_prophecy_btrack_recommended_eval_chain_v1.py"


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


def _score_eval(per_date: Path, slug: str) -> tuple[Path, Path, dict[str, Any]]:
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
    m = (_load(ev).get("metrics") or {}) if ev.is_file() else {}
    return score, ev, {
        "price_directional_hit_rate": m.get("price_directional_hit_rate"),
        "n_evaluated": m.get("n_evaluated"),
        "price_hits": m.get("price_hits"),
    }


def _patch_flip_v1(base_per: Path, legacy_per: Path, out_per: Path) -> dict[str, Any]:
    base = _load(base_per)
    legacy_map = _dir_map(_load(legacy_per))
    patched = 0
    rows: list[dict[str, Any]] = []
    for row in base.get("rows") or []:
        if not isinstance(row, dict):
            continue
        r = copy.deepcopy(row)
        ed = str(r.get("eval_date") or "")[:10]
        if ed in FLIP_DATES and ed in legacy_map:
            old = str(r.get("predicted_direction") or "neutral").lower()
            new = legacy_map[ed]
            if old != new:
                patched += 1
            r["predicted_direction"] = new
            r["flip_patch_v1"] = {"from": old, "to": new, "source": "legacy_v1"}
        rows.append(r)
    doc = copy.deepcopy(base)
    doc["rows"] = rows
    doc["flip_patch_meta"] = {
        "flip_dates": list(FLIP_DATES),
        "n_direction_patched": patched,
        "research_only": True,
    }
    out_per.parent.mkdir(parents=True, exist_ok=True)
    out_per.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"n_patched": patched, "out": str(out_per)}


def _task_flip_patch_solo() -> dict[str, Any]:
    out = WORK / "per_date_m016_flip_patch.json"
    meta = _patch_flip_v1(M016_PER, LEGACY_V1, out)
    _, _, metrics = _score_eval(out, "flip_patch_solo")
    return {
        "task": "flip_patch_solo",
        "exit_code": 0,
        "summary": {**meta, **metrics, "baseline_m016_solo": 0.533333},
    }


def _task_flip_patch_hybrid() -> dict[str, Any]:
    from scripts.run_btrack_v1_ms_hybrid_parallel_v1 import (
        HYBRID_RULES,
        _merge_agree_or_ms_else_v1,
        build_hybrid_rows,
    )

    legacy_map = _dir_map(_load(LEGACY_V1))
    m016_map = _dir_map(_load(M016_PER))
    ms_map = _dir_map(_load(MS_PER))
    dates = _anchor_dates()
    patched_map = dict(m016_map)
    for ed in FLIP_DATES:
        if ed in legacy_map:
            patched_map[ed] = legacy_map[ed]

    per_out = WORK / "per_date_m016_hybrid_flip_patch.json"
    doc = {
        "schema": "btrack_ensemble_per_date_directions_v1",
        "version": "1.0.0",
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "ts_utc": _utc(),
        "ensemble_mode": "hybrid_agree_or_ms_else_v1_flip_patch",
        "research_only": True,
        "hybrid_rule": "agree_or_ms_else_v1",
        "flip_patch_meta": {"flip_dates": list(FLIP_DATES), "v1_source": "margin_016_with_legacy_on_flip"},
        "rows": build_hybrid_rows(
            dates=dates,
            v1_map=patched_map,
            ms_map=ms_map,
            rule_id="agree_or_ms_else_v1",
            merge_fn=_merge_agree_or_ms_else_v1,
        ),
    }
    per_out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _, _, metrics = _score_eval(per_out, "flip_patch_hybrid")
    legacy_hybrid_rate = 0.6
    return {
        "task": "flip_patch_hybrid",
        "exit_code": 0,
        "summary": {
            **metrics,
            "baseline_m016_hybrid": 0.533333,
            "legacy_hybrid_reference": legacy_hybrid_rate,
            "reaches_legacy_hybrid": metrics.get("price_directional_hit_rate") == legacy_hybrid_rate,
        },
    }


def _task_rolling_holdout() -> dict[str, Any]:
    from scripts.run_btrack_frozen30d_parallel_bundle_v3 import _btc_rows, _window_metrics

    paths = {
        "legacy_hybrid": ROOT / "reports/btrack_v1_ms_hybrid_work/agree_or_ms_else_v1/score.json",
        "m016_hybrid": ROOT / "reports/btrack_v1_ms_hybrid_margin016_work/agree_or_ms_else_v1/score.json",
        "m016_solo": ROOT / "reports/btrack_frozen30d_margin_fine_sweep_work/score_margin_016.json",
        "flip_patch_hybrid": WORK / "flip_patch_hybrid/score.json",
    }
    dates = _anchor_dates()
    if len(dates) < 10:
        return {"task": "rolling_holdout", "exit_code": 2, "error": "too few dates"}

    window_size = 5
    step = 5
    windows: list[dict[str, Any]] = []
    for start in range(0, len(dates) - window_size + 1, step):
        chunk = dates[start : start + window_size]
        if len(chunk) < window_size:
            break
        win: dict[str, Any] = {"dates": chunk, "lanes": {}}
        for name, p in paths.items():
            if not p.is_file():
                continue
            win["lanes"][name] = _window_metrics(_btc_rows(p), chunk)
        windows.append(win)

    # Also 3-day sliding (more granular)
    slide3: list[dict[str, Any]] = []
    for i in range(len(dates) - 2):
        chunk = dates[i : i + 3]
        slide3.append(
            {
                "dates": chunk,
                "legacy_hybrid": _window_metrics(_btc_rows(paths["legacy_hybrid"]), chunk)
                if paths["legacy_hybrid"].is_file()
                else None,
                "m016_hybrid": _window_metrics(_btc_rows(paths["m016_hybrid"]), chunk)
                if paths["m016_hybrid"].is_file()
                else None,
            }
        )

    out = ROOT / "reports/btrack_frozen30d_rolling_holdout_v1_latest.json"
    report = {
        "schema": "btrack_frozen30d_rolling_holdout_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "window_size_5d_step_5": windows,
        "window_size_3d_slide_1": slide3,
        "aggregate_5d": _aggregate_windows(windows),
    }
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"task": "rolling_holdout", "exit_code": 0, "report": str(out), "summary": report["aggregate_5d"]}


def _aggregate_windows(windows: list[dict[str, Any]]) -> dict[str, Any]:
    lanes: dict[str, list[float]] = {}
    for w in windows:
        for lane, m in (w.get("lanes") or {}).items():
            hr = (m or {}).get("price_directional_hit_rate")
            if hr is not None:
                lanes.setdefault(lane, []).append(float(hr))
    return {
        lane: {
            "n_windows": len(vals),
            "mean_hit_rate": round(sum(vals) / len(vals), 6) if vals else None,
            "min": min(vals) if vals else None,
            "max": max(vals) if vals else None,
        }
        for lane, vals in lanes.items()
    }


def _task_force_neutral_holdout_ovn() -> dict[str, Any]:
    """force_neutral holdout_ovn_signed_bull layer on m016 solo (full 30d)."""
    from scripts.btrack_wrong_dir_auxiliary_layer_v1 import apply_auxiliary_per_date_doc
    from scripts.run_btrack_wrong_dir_holdout_v1 import enrich_per_date_doc_btc

    layer = {
        "enabled": True,
        "action": "force_neutral",
        "apply_when": {
            "holdout_only": True,
            "preliminary_bull": True,
            "overnight_negative_or_positive": True,
        },
    }
    per_doc = enrich_per_date_doc_btc(_load(M016_PER), str(BTC.relative_to(ROOT)))
    adj = apply_auxiliary_per_date_doc(per_doc, layer)
    out = WORK / "per_date_m016_holdout_ovn_neutral.json"
    out.write_text(json.dumps(adj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    gated = sum(
        1
        for r in adj.get("rows") or []
        if isinstance(r, dict) and str(r.get("predicted_direction") or "").lower() == "neutral"
    )
    _, _, metrics = _score_eval(out, "force_neutral_holdout_ovn")
    return {
        "task": "force_neutral_holdout_ovn",
        "exit_code": 0,
        "summary": {**metrics, "gated_neutral_count": gated, "baseline_m016_solo": 0.533333},
    }


def _task_promotion_gates_flip_patch() -> dict[str, Any]:
    per = WORK / "per_date_m016_flip_patch.json"
    if not per.is_file():
        return {"task": "promotion_gates_flip_patch", "exit_code": 2, "error": "run flip_patch_solo first"}
    gates_out = WORK / "promotion_gates_flip_patch.json"
    summary_out = WORK / "recommended_chain_summary_flip_patch.json"
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
            str(summary_out.relative_to(ROOT)),
            "--calibration-note",
            "frozen30d_flip_patch_margin016",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    gates = _load(gates_out) if gates_out.is_file() else {}
    return {
        "task": "promotion_gates_flip_patch",
        "exit_code": proc.returncode,
        "summary": {
            "combined_all_passed": bool(gates.get("combined_all_passed")),
            "outcome_class": gates.get("outcome_class"),
        },
        "stderr_tail": (proc.stderr or "")[-400:] if proc.returncode else None,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    WORK.mkdir(parents=True, exist_ok=True)

    # Phase 1: flip patches (hybrid depends on solo patch file only for ordering; run solo first in serial mini-phase)
    phase1 = [_task_flip_patch_solo, _task_flip_patch_hybrid]
    phase1_results: list[dict[str, Any]] = []
    for fn in phase1:
        phase1_results.append(fn())

    phase2_fns = [
        _task_rolling_holdout,
        _task_force_neutral_holdout_ovn,
        _task_promotion_gates_flip_patch,
    ]
    phase2_results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(fn): fn.__name__ for fn in phase2_fns}
        for fut in as_completed(futures):
            try:
                phase2_results.append(fut.result())
            except Exception as exc:
                phase2_results.append({"task": futures[fut], "exit_code": 2, "error": str(exc)})

    results = phase1_results + phase2_results
    bundle = {
        "schema": "btrack_frozen30d_parallel_bundle_v5",
        "generated_at_utc": _utc(),
        "research_only": True,
        "track_a_auto_promote": False,
        "flip_dates": list(FLIP_DATES),
        "parallel_tasks": results,
    }
    args.output.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    for r in results:
        print(f"  {r.get('task')}: exit={r.get('exit_code')} {r.get('summary', r.get('error', ''))}")
    return 0 if all(int(r.get("exit_code", 1)) == 0 for r in results) else 2


if __name__ == "__main__":
    raise SystemExit(main())
