#!/usr/bin/env python3
"""[HYPO] Parallel bundle v2: margin_016 MS hybrid + micro margin + promotion gates."""
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

DEFAULT_OUT = ROOT / "reports/btrack_frozen30d_parallel_bundle_v2_latest.json"
MARGIN_016_PER_DATE = ROOT / "reports/btrack_frozen30d_margin_fine_sweep_work/per_date_margin_016.json"
REC_CHAIN = ROOT / "scripts/run_prophecy_btrack_recommended_eval_chain_v1.py"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _task_hybrid(v1_path: Path, label: str, out: Path, work: Path) -> dict[str, Any]:
    from scripts.run_btrack_v1_ms_hybrid_parallel_v1 import (
        HYBRID_RULES,
        _dir_map,
        _load,
        _run_lane,
        ANCHOR_DATES,
        ANCHOR_SCORE,
        MS_PER_DATE,
        BTC,
        HYP,
    )

    work.mkdir(parents=True, exist_ok=True)
    for p in (ANCHOR_SCORE, v1_path, MS_PER_DATE, HYP, BTC):
        if not p.is_file():
            return {"task": f"hybrid_{label}", "exit_code": 2, "error": f"missing {p}"}

    dates = list(_load(ANCHOR_DATES).get("eval_dates") or [])
    if not dates:
        anchor = _load(ANCHOR_SCORE)
        dates = sorted(
            {
                str(r.get("eval_date") or "")[:10]
                for r in anchor.get("rows") or []
                if str(r.get("instrument") or "").lower() == "btc"
            }
        )
    v1_map = _dir_map(_load(v1_path))
    ms_map = _dir_map(_load(MS_PER_DATE))
    py = sys.executable

    import scripts.run_btrack_v1_ms_hybrid_parallel_v1 as hybrid_mod

    orig_work = hybrid_mod.WORK
    hybrid_mod.WORK = work
    try:
        lanes: list[dict[str, Any]] = []
        with ThreadPoolExecutor(max_workers=5) as pool:
            futures = {
                pool.submit(
                    _run_lane,
                    rule_id=rid,
                    dates=dates,
                    v1_map=v1_map,
                    ms_map=ms_map,
                    merge_fn=fn,
                    py=py,
                ): rid
                for rid, (_desc, fn) in HYBRID_RULES.items()
            }
            for fut in as_completed(futures):
                rid = futures[fut]
                try:
                    lanes.append(fut.result())
                except Exception as exc:
                    lanes.append({"rule_id": rid, "error": str(exc)})

        best = None
        for lane in lanes:
            if lane.get("error"):
                continue
            rate = (lane.get("metrics") or {}).get("all_rows")
            if rate is None:
                continue
            if best is None or float(rate) > float((best.get("metrics") or {}).get("all_rows") or -1):
                best = lane

        pack = {
            "schema": f"btrack_v1_ms_hybrid_{label}_parallel_v1",
            "generated_at_utc": _utc(),
            "research_only": True,
            "v1_per_date": str(v1_path.relative_to(ROOT)).replace("\\", "/"),
            "lanes": lanes,
            "best_all_rows_lane": best.get("rule_id") if best else None,
            "best_all_rows": (best.get("metrics") or {}).get("all_rows") if best else None,
            "legacy_reference_agree_or_ms_else_v1": 0.6,
        }
        out.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return {
            "task": f"hybrid_{label}",
            "exit_code": 0 if all(not lane.get("error") for lane in lanes) else 2,
            "report": str(out),
            "summary": {"best_rule": pack.get("best_all_rows_lane"), "best_all_rows": pack.get("best_all_rows")},
        }
    finally:
        hybrid_mod.WORK = orig_work


def _task_micro_margin() -> dict[str, Any]:
    from scripts.run_btrack_frozen30d_margin_penalty_grid_v1 import (
        _anchor_dates,
        _apply_cfg,
        _load,
        _run_variant,
        ANCHOR_SCORE,
        BASELINE_EVAL,
        DEFAULT_CFG,
    )

    specs = [
        {"slug": f"margin_{int(m * 1000):03d}", "tie_break_min_margin": m}
        for m in (0.012, 0.014, 0.015, 0.017)
    ]
    work = ROOT / "reports/btrack_frozen30d_margin_micro_sweep_work"
    out = ROOT / "reports/btrack_frozen30d_margin_micro_sweep_v1_latest.json"
    work.mkdir(parents=True, exist_ok=True)
    dates = _anchor_dates(ANCHOR_SCORE)
    dates_path = work / "anchor_eval_dates.json"
    dates_path.write_text(json.dumps({"eval_dates": dates}, indent=2) + "\n", encoding="utf-8")
    base_m = (_load(BASELINE_EVAL).get("metrics") or {})
    rows: list[dict[str, Any]] = []
    for spec in specs:
        try:
            row = _run_variant(
                spec,
                base_cfg=_load(DEFAULT_CFG),
                dates_path=dates_path,
                anchor_score=ANCHOR_SCORE,
                work_dir=work,
            )
            hr = float(
                (row.get("metrics") or {}).get("price_directional_hit_rate")
                or (row.get("score_derived") or {}).get("all_rows_hit_rate")
                or 0
            )
            row["delta_vs_frozen_kpi_a"] = {
                "price_directional_hit_rate": round(hr - float(base_m.get("price_directional_hit_rate") or 0), 6)
            }
            rows.append(row)
        except RuntimeError as e:
            rows.append({"slug": spec["slug"], "error": str(e)[:400]})

    ok = [r for r in rows if "metrics" in r]

    def _hr(r: dict[str, Any]) -> float:
        return float(
            (r.get("metrics") or {}).get("price_directional_hit_rate")
            or (r.get("score_derived") or {}).get("all_rows_hit_rate")
            or 0
        )

    best = max(ok, key=_hr) if ok else None
    report = {
        "schema": "btrack_frozen30d_margin_micro_sweep_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "variants": rows,
        "best_slug": best["slug"] if best else None,
        "best_all_rows": _hr(best) if best else None,
        "prior_best_margin_016": 0.533333,
    }
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"task": "micro_margin", "exit_code": 0, "report": str(out), "summary": report}


def _task_promotion_gates_margin016() -> dict[str, Any]:
    if not MARGIN_016_PER_DATE.is_file():
        return {"task": "promotion_gates_margin016", "exit_code": 2, "error": "missing margin_016 per_date"}
    work = ROOT / "reports/btrack_frozen30d_parallel_bundle_v2_work"
    work.mkdir(parents=True, exist_ok=True)
    gates_out = work / "promotion_gates_margin_016.json"
    summary_out = work / "recommended_chain_summary_margin_016.json"
    cmd = [
        sys.executable,
        str(REC_CHAIN),
        "--recent-trading-days",
        "180",
        "--per-date-direction-json",
        str(MARGIN_016_PER_DATE.relative_to(ROOT)),
        "--gates-out",
        str(gates_out.relative_to(ROOT)),
        "--summary-out",
        str(summary_out.relative_to(ROOT)),
        "--calibration-note",
        "frozen30d_margin_016_per_date",
    ]
    rc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    gates = _load(gates_out) if gates_out.is_file() else {}
    return {
        "task": "promotion_gates_margin016",
        "exit_code": rc.returncode,
        "report": str(gates_out),
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
        "stderr_tail": (rc.stderr or "")[-500:] if rc.returncode != 0 else None,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    tasks = [
        lambda: _task_hybrid(
            MARGIN_016_PER_DATE,
            "margin016",
            ROOT / "reports/btrack_v1_ms_hybrid_margin016_parallel_v1_latest.json",
            ROOT / "reports/btrack_v1_ms_hybrid_margin016_work",
        ),
        _task_micro_margin,
        _task_promotion_gates_margin016,
    ]
    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(fn): i for i, fn in enumerate(tasks)}
        for fut in as_completed(futures):
            try:
                results.append(fut.result())
            except Exception as exc:
                results.append({"task": "unknown", "exit_code": 2, "error": str(exc)})

    bundle = {
        "schema": "btrack_frozen30d_parallel_bundle_v2",
        "generated_at_utc": _utc(),
        "research_only": True,
        "track_a_auto_promote": False,
        "parallel_tasks": results,
        "leaderboard_hint": {
            "frozen_kpi_a": 0.433333,
            "v1_margin016_solo": 0.533333,
            "legacy_ms_hybrid": 0.6,
            "ms_margin020_hybrid": 0.533333,
        },
    }
    args.output.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    for r in results:
        print(f"  {r.get('task')}: exit={r.get('exit_code')} {r.get('summary', r.get('error', ''))}")
    return 0 if all(int(r.get("exit_code", 1)) == 0 for r in results) else 2


if __name__ == "__main__":
    raise SystemExit(main())
