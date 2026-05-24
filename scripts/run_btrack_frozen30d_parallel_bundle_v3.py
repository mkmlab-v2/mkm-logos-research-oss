#!/usr/bin/env python3
"""[HYPO] Parallel bundle v3: daily diff (60% vs 53.3%) + pseudo-holdout split + MS lift."""
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

DEFAULT_OUT = ROOT / "reports/btrack_frozen30d_parallel_bundle_v3_latest.json"
ANCHOR_SCORE = ROOT / "reports/btrack_prophecy_score_30d_frozen_kpi_a_v1.json"
LEGACY_HYBRID_SCORE = ROOT / "reports/btrack_v1_ms_hybrid_work/agree_or_ms_else_v1/score.json"
LEGACY_HYBRID_PER = ROOT / "reports/btrack_v1_ms_hybrid_work/agree_or_ms_else_v1/per_date.json"
M016_HYBRID_SCORE = ROOT / "reports/btrack_v1_ms_hybrid_margin016_work/agree_or_ms_else_v1/score.json"
M016_HYBRID_PER = ROOT / "reports/btrack_v1_ms_hybrid_margin016_work/agree_or_ms_else_v1/per_date.json"
M016_SOLO_SCORE = ROOT / "reports/btrack_frozen30d_margin_fine_sweep_work/score_margin_016.json"
M012_SOLO_SCORE = ROOT / "reports/btrack_frozen30d_margin_micro_sweep_work/score_margin_012.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _btc_rows(score_path: Path) -> dict[str, dict[str, Any]]:
    doc = _load(score_path)
    out: dict[str, dict[str, Any]] = {}
    for r in doc.get("rows") or []:
        if not isinstance(r, dict):
            continue
        if str(r.get("instrument") or "").lower() != "btc":
            continue
        ed = str(r.get("eval_date") or "")[:10]
        if ed:
            out[ed] = r
    return out


def _per_sources(per_path: Path) -> dict[str, dict[str, str]]:
    doc = _load(per_path)
    out: dict[str, dict[str, str]] = {}
    for r in doc.get("rows") or []:
        if not isinstance(r, dict):
            continue
        ed = str(r.get("eval_date") or "")[:10]
        src = r.get("sources") if isinstance(r.get("sources"), dict) else {}
        out[ed] = {
            "v1": str(src.get("v1") or r.get("predicted_direction") or "neutral").lower(),
            "ms": str(src.get("ms") or "neutral").lower(),
            "hybrid": str(r.get("predicted_direction") or "neutral").lower(),
        }
    return out


def _hit(pred: str, act: str) -> bool | None:
    p, a = pred.lower(), act.lower()
    if p not in ("bull", "bear") or a not in ("bull", "bear"):
        return None
    return p == a


def _window_metrics(rows_by_date: dict[str, dict[str, Any]], dates: list[str]) -> dict[str, Any]:
    n = hits = 0
    for d in dates:
        r = rows_by_date.get(d)
        if not r:
            continue
        pred = str(r.get("predicted_direction") or "neutral").lower()
        act = str(r.get("actual_direction") or "neutral").lower()
        h = _hit(pred, act)
        if h is None:
            continue
        n += 1
        if h:
            hits += 1
    return {
        "n_evaluated": n,
        "price_hits": hits,
        "price_directional_hit_rate": round(hits / n, 6) if n else None,
    }


def _task_daily_diff() -> dict[str, Any]:
    paths = {
        "frozen_kpi_a": ANCHOR_SCORE,
        "legacy_hybrid": LEGACY_HYBRID_SCORE,
        "m016_hybrid": M016_HYBRID_SCORE,
        "m016_solo": M016_SOLO_SCORE,
    }
    for p in paths.values():
        if not p.is_file():
            return {"task": "daily_diff", "exit_code": 2, "error": f"missing {p}"}

    frozen = _btc_rows(ANCHOR_SCORE)
    leg_h = _btc_rows(LEGACY_HYBRID_SCORE)
    m16_h = _btc_rows(M016_HYBRID_SCORE)
    m16_s = _btc_rows(M016_SOLO_SCORE)
    leg_src = _per_sources(LEGACY_HYBRID_PER)
    m16_src = _per_sources(M016_HYBRID_PER)

    dates = sorted(set(frozen) | set(leg_h) | set(m16_h) | set(m16_s))
    day_rows: list[dict[str, Any]] = []
    counts = {
        "legacy_hybrid_only_hit": 0,
        "m016_hybrid_only_hit": 0,
        "both_hybrid_hit": 0,
        "both_hybrid_miss": 0,
        "ms_overrode_v1_legacy_win": 0,
        "ms_overrode_v1_legacy_loss": 0,
        "v1_margin_change_flipped_outcome": 0,
    }

    for ed in dates:
        act = str((frozen.get(ed) or leg_h.get(ed) or {}).get("actual_direction") or "neutral").lower()
        fr = frozen.get(ed, {})
        lh = leg_h.get(ed, {})
        mh = m16_h.get(ed, {})
        ms = m16_s.get(ed, {})
        lp = str(lh.get("predicted_direction") or "neutral").lower()
        mp = str(mh.get("predicted_direction") or "neutral").lower()
        sp = str(ms.get("predicted_direction") or "neutral").lower()
        fp = str(fr.get("predicted_direction") or "neutral").lower()
        lh_hit = _hit(lp, act)
        mh_hit = _hit(mp, act)
        sh_hit = _hit(sp, act)
        lsrc = leg_src.get(ed, {})
        msrc = m16_src.get(ed, {})
        v1_changed = lsrc.get("v1") != msrc.get("v1")
        hybrid_changed = lp != mp

        if lh_hit and not mh_hit:
            counts["legacy_hybrid_only_hit"] += 1
        if mh_hit and not lh_hit:
            counts["m016_hybrid_only_hit"] += 1
        if lh_hit and mh_hit:
            counts["both_hybrid_hit"] += 1
        if lh_hit is False and mh_hit is False:
            counts["both_hybrid_miss"] += 1

        # MS picked direction when v1 sources disagree with final legacy hybrid
        if lsrc.get("ms") in ("bull", "bear") and lsrc.get("v1") != lsrc.get("ms"):
            if lh_hit and lsrc.get("ms") == act:
                counts["ms_overrode_v1_legacy_win"] += 1
            if lh_hit is False and lsrc.get("ms") == act:
                counts["ms_overrode_v1_legacy_loss"] += 1

        if v1_changed and hybrid_changed and lh_hit != mh_hit:
            counts["v1_margin_change_flipped_outcome"] += 1

        day_rows.append(
            {
                "eval_date": ed,
                "actual": act,
                "frozen_kpi_pred": fp,
                "legacy_hybrid_pred": lp,
                "m016_hybrid_pred": mp,
                "m016_solo_pred": sp,
                "legacy_v1": lsrc.get("v1"),
                "legacy_ms": lsrc.get("ms"),
                "m016_v1": msrc.get("v1"),
                "m016_ms": msrc.get("ms"),
                "legacy_hybrid_hit": lh_hit,
                "m016_hybrid_hit": mh_hit,
                "m016_solo_hit": sh_hit,
                "v1_inputs_differ": v1_changed,
                "hybrid_output_differ": hybrid_changed,
            }
        )

    leg_all = _window_metrics(leg_h, dates)
    m16_all = _window_metrics(m16_h, dates)
    solo_all = _window_metrics(m16_s, dates)

    out = ROOT / "reports/btrack_frozen30d_hybrid_daily_diff_v1_latest.json"
    report = {
        "schema": "btrack_frozen30d_hybrid_daily_diff_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "summary": {
            "n_days": len(dates),
            "legacy_hybrid_all_rows": leg_all.get("price_directional_hit_rate"),
            "m016_hybrid_all_rows": m16_all.get("price_directional_hit_rate"),
            "m016_solo_all_rows": solo_all.get("price_directional_hit_rate"),
            "delta_legacy_minus_m016_hybrid": round(
                float(leg_all.get("price_directional_hit_rate") or 0)
                - float(m16_all.get("price_directional_hit_rate") or 0),
                6,
            ),
            **counts,
        },
        "per_day": day_rows,
        "insight": (
            "60% vs 53.3% gap is driven by days where legacy v1+MS hybrid differs from "
            "margin_016 v1+MS; see legacy_hybrid_only_hit vs m016_hybrid_only_hit."
        ),
    }
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"task": "daily_diff", "exit_code": 0, "report": str(out), "summary": report["summary"]}


def _task_pseudo_holdout() -> dict[str, Any]:
    if not LEGACY_HYBRID_SCORE.is_file() or not M016_SOLO_SCORE.is_file():
        return {"task": "pseudo_holdout", "exit_code": 2, "error": "missing score files"}

    dates = sorted(_btc_rows(ANCHOR_SCORE).keys())
    if len(dates) < 20:
        return {"task": "pseudo_holdout", "exit_code": 2, "error": "too few dates"}

    mid = len(dates) // 2
    train = dates[:mid]
    test = dates[mid:]

    leg = _btc_rows(LEGACY_HYBRID_SCORE)
    m16h = _btc_rows(M016_HYBRID_SCORE)
    m16s = _btc_rows(M016_SOLO_SCORE)
    m12s = _btc_rows(M012_SOLO_SCORE) if M012_SOLO_SCORE.is_file() else {}

    lanes = {
        "legacy_hybrid": leg,
        "m016_hybrid": m16h,
        "m016_solo": m16s,
    }
    if m12s:
        lanes["m012_solo"] = m12s

    windows: dict[str, Any] = {}
    for name, rows in lanes.items():
        windows[name] = {
            "train_first_half": _window_metrics(rows, train),
            "test_second_half": _window_metrics(rows, test),
            "full_panel": _window_metrics(rows, dates),
        }

    out = ROOT / "reports/btrack_frozen30d_pseudo_holdout_v1_latest.json"
    report = {
        "schema": "btrack_frozen30d_pseudo_holdout_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "split": {"train_dates": train, "test_dates": test, "n_train": len(train), "n_test": len(test)},
        "windows": windows,
        "note": "Chronological 50/50 split on frozen anchor dates; not true OOS registration.",
    }
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"task": "pseudo_holdout", "exit_code": 0, "report": str(out), "summary": windows}


def _task_rebuild_legacy_hybrid_baseline() -> dict[str, Any]:
    """Re-run legacy MS hybrid to refresh score if stale (parallel sanity)."""
    from scripts.run_btrack_v1_ms_hybrid_parallel_v1 import main as hybrid_main

    out_path = ROOT / "reports/btrack_v1_ms_hybrid_parallel_refresh_v1_latest.json"
    # Run hybrid main only for agree_or_ms_else - full script refreshes all lanes
    rc = hybrid_main()
    pack = _load(ROOT / "reports/btrack_v1_ms_hybrid_parallel_v1_latest.json") if (
        ROOT / "reports/btrack_v1_ms_hybrid_parallel_v1_latest.json"
    ).is_file() else {}
    best = pack.get("best_all_rows")
    return {
        "task": "refresh_legacy_hybrid",
        "exit_code": rc,
        "summary": {"best_all_rows_lane": pack.get("best_all_rows_lane"), "best_all_rows": best},
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--skip-refresh", action="store_true")
    args = ap.parse_args()

    tasks = [_task_daily_diff, _task_pseudo_holdout]
    if not args.skip_refresh:
        tasks.append(_task_rebuild_legacy_hybrid_baseline)

    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=len(tasks)) as pool:
        futures = {pool.submit(fn): fn.__name__ for fn in tasks}
        for fut in as_completed(futures):
            try:
                results.append(fut.result())
            except Exception as exc:
                results.append({"task": futures[fut], "exit_code": 2, "error": str(exc)})

    bundle = {
        "schema": "btrack_frozen30d_parallel_bundle_v3",
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
