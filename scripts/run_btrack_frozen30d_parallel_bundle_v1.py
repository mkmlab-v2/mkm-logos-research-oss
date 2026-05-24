#!/usr/bin/env python3
"""[HYPO] Parallel bundle: fine margin sweep + MS hybrid on margin_020 v1 (frozen 30d)."""
from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_OUT = ROOT / "reports/btrack_frozen30d_parallel_bundle_v1_latest.json"
MARGIN_020_PER_DATE = ROOT / "reports/btrack_frozen30d_margin_penalty_grid_work/per_date_margin_020.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _task_fine_margin() -> dict[str, Any]:
    from scripts.run_btrack_frozen30d_margin_penalty_grid_v1 import (
        VARIANTS,
        _anchor_dates,
        _apply_cfg,
        _load,
        _run_variant,
        ANCHOR_SCORE,
        BASELINE_EVAL,
        DEFAULT_CFG,
    )

    fine_specs = [
        {"slug": f"margin_{int(m * 1000):03d}", "tie_break_min_margin": m}
        for m in (0.016, 0.018, 0.020, 0.022, 0.024, 0.026, 0.028, 0.030)
    ]
    work = ROOT / "reports/btrack_frozen30d_margin_fine_sweep_work"
    out = ROOT / "reports/btrack_frozen30d_margin_fine_sweep_v1_latest.json"
    work.mkdir(parents=True, exist_ok=True)
    dates = _anchor_dates(ANCHOR_SCORE)
    dates_path = work / "anchor_eval_dates.json"
    dates_path.write_text(json.dumps({"eval_dates": dates}, indent=2) + "\n", encoding="utf-8")
    base_cfg = _load(DEFAULT_CFG)
    base_m = _load(BASELINE_EVAL).get("metrics") or {}
    rows: list[dict[str, Any]] = []
    for spec in fine_specs:
        try:
            row = _run_variant(
                spec,
                base_cfg=base_cfg,
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
        "schema": "btrack_frozen30d_margin_fine_sweep_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "variants": rows,
        "best_by_all_rows_hit_rate": best["slug"] if best else None,
        "best_all_rows": _hr(best) if best else None,
        "best_alert_1_pass": bool(best and _hr(best) >= 0.5),
        "output_path": str(out),
    }
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"task": "fine_margin_sweep", "exit_code": 0, "report": str(out), "summary": report}


def _task_hybrid_margin020() -> dict[str, Any]:
    from concurrent.futures import ThreadPoolExecutor, as_completed

    from scripts.run_btrack_v1_ms_hybrid_parallel_v1 import (
        HYBRID_RULES,
        _dir_map,
        _eval_metrics,
        _load,
        _run_lane,
        ANCHOR_DATES,
        ANCHOR_SCORE,
        MS_PER_DATE,
        BTC,
        HYP,
    )

    v1_path = MARGIN_020_PER_DATE
    out = ROOT / "reports/btrack_v1_ms_hybrid_margin020_parallel_v1_latest.json"
    work = ROOT / "reports/btrack_v1_ms_hybrid_margin020_work"
    work.mkdir(parents=True, exist_ok=True)

    for p in (ANCHOR_SCORE, v1_path, MS_PER_DATE, HYP, BTC):
        if not p.is_file():
            return {
                "task": "hybrid_margin020",
                "exit_code": 2,
                "error": f"missing {p}",
            }

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

    # Patch WORK for hybrid lanes under margin020 work dir
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

        lanes.sort(key=lambda x: str(x.get("rule_id") or ""))
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
            "schema": "btrack_v1_ms_hybrid_margin020_parallel_v1",
            "generated_at_utc": _utc(),
            "research_only": True,
            "hypothesis_tag": "[HYPO]",
            "v1_per_date_source": "margin_020 (tie_break_min_margin=0.02)",
            "panel": {
                "n_days": len(dates),
                "v1_per_date": str(v1_path.relative_to(ROOT)).replace("\\", "/"),
                "ms_per_date": str(MS_PER_DATE.relative_to(ROOT)).replace("\\", "/"),
            },
            "baseline_reference": {
                "frozen_kpi_a_all_rows": 0.433333,
                "v1_margin020_alone": 0.5,
                "legacy_hybrid_agree_or_ms_else_v1": 0.6,
            },
            "lanes": lanes,
            "best_all_rows_lane": best.get("rule_id") if best else None,
            "best_all_rows": (best.get("metrics") or {}).get("all_rows") if best else None,
        }
        out.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return {
            "task": "hybrid_margin020",
            "exit_code": 0 if all(not lane.get("error") for lane in lanes) else 2,
            "report": str(out),
            "summary": {
                "best_rule": pack.get("best_all_rows_lane"),
                "best_all_rows": pack.get("best_all_rows"),
            },
        }
    finally:
        hybrid_mod.WORK = orig_work


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--workers", type=int, default=2, help="Parallel tasks (fine margin + hybrid).")
    args = ap.parse_args()

    tasks = [_task_fine_margin, _task_hybrid_margin020]
    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=min(args.workers, len(tasks))) as pool:
        futures = {pool.submit(fn): fn.__name__ for fn in tasks}
        for fut in as_completed(futures):
            name = futures[fut]
            try:
                results.append(fut.result())
            except Exception as exc:
                results.append({"task": name, "exit_code": 2, "error": str(exc)})

    bundle = {
        "schema": "btrack_frozen30d_parallel_bundle_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "track_a_auto_promote": False,
        "parallel_tasks": results,
        "note": "Fine margin 0.016-0.030 + MS×margin_020 hybrid rules in parallel.",
    }
    args.output.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    for r in results:
        print(f"  {r.get('task')}: exit={r.get('exit_code')} {r.get('summary', r.get('error', ''))}")
    return 0 if all(int(r.get("exit_code", 1)) == 0 for r in results) else 2


if __name__ == "__main__":
    raise SystemExit(main())
