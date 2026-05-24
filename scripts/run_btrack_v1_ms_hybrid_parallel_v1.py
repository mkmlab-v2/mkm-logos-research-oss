#!/usr/bin/env python3
"""[HYPO] Parallel v1+MS hybrid per-date rules on anchor 30d panel (B-track research)."""
from __future__ import annotations

import argparse
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

ANCHOR_SCORE = ROOT / "reports/btrack_prophecy_score_30d_frozen_kpi_a_v1.json"
ANCHOR_DATES = ROOT / "reports/btrack_anchor_eval_dates_v1.json"
V1_PER_DATE = ROOT / "reports/btrack_ensemble_per_date_v1_prod_perdate_30d_v1.json"
MS_PER_DATE = ROOT / "reports/btrack_lens_combo_ms_per_date_anchor_v1.json"
HYP = ROOT / "docs/final/artifacts/btrack_hypothesis_prophecy_latest.json"
BTC = ROOT / "research/market_data/btc_daily_external_yf.csv"
WORK = ROOT / "reports/btrack_v1_ms_hybrid_work"
OUT = ROOT / "reports/btrack_v1_ms_hybrid_parallel_v1_latest.json"
SHADOW_EVAL = ROOT / "reports/prophecy_hit_rate_eval_v1_shadow_anchor_30d_v1.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(p.resolve())


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


def _is_dir(d: str) -> bool:
    return d in ("bull", "bear")


def _merge_ms_when_active_else_v1(v1: str, ms: str) -> str:
    return ms if _is_dir(ms) else v1


def _merge_agree_only(v1: str, ms: str) -> str:
    if _is_dir(v1) and v1 == ms:
        return v1
    return "neutral"


def _merge_agree_or_ms_else_v1(v1: str, ms: str) -> str:
    if _is_dir(v1) and v1 == ms:
        return v1
    if _is_dir(ms):
        return ms
    return v1 if _is_dir(v1) else "neutral"


def _merge_ms_on_conflict_else_v1(v1: str, ms: str) -> str:
    if _is_dir(ms) and _is_dir(v1) and ms != v1:
        return ms
    if _is_dir(ms):
        return ms
    return v1


def _merge_v1_unless_ms_agrees(v1: str, ms: str) -> str:
    if _is_dir(ms) and _is_dir(v1):
        return ms if ms == v1 else v1
    if _is_dir(ms) and not _is_dir(v1):
        return ms
    return v1


HYBRID_RULES: dict[str, tuple[str, Callable[[str, str], str]]] = {
    "ms_when_active_else_v1": (
        "MS directional days use MS; otherwise v1 per-date.",
        _merge_ms_when_active_else_v1,
    ),
    "agree_only_else_neutral": (
        "bull/bear only when v1 and MS agree; else neutral.",
        _merge_agree_only,
    ),
    "agree_or_ms_else_v1": (
        "Agreement wins; else MS if active; else v1.",
        _merge_agree_or_ms_else_v1,
    ),
    "ms_wins_on_conflict": (
        "MS when active; on v1/MS conflict prefer MS.",
        _merge_ms_on_conflict_else_v1,
    ),
    "v1_unless_ms_agrees": (
        "v1 default; MS only when both directional and equal.",
        _merge_v1_unless_ms_agrees,
    ),
}


def build_hybrid_rows(
    *,
    dates: list[str],
    v1_map: dict[str, str],
    ms_map: dict[str, str],
    rule_id: str,
    merge_fn: Callable[[str, str], str],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for ed in dates:
        v1 = v1_map.get(ed, "neutral")
        ms = ms_map.get(ed, "neutral")
        pred = merge_fn(v1, ms)
        rows.append(
            {
                "eval_date": ed,
                "instrument": "btc",
                "predicted_direction": pred,
                "ensemble_mode": f"hybrid_{rule_id}_v1",
                "hybrid_rule": rule_id,
                "sources": {"v1": v1, "ms": ms},
            }
        )
    return rows


def _eval_metrics(eval_path: Path) -> dict[str, Any]:
    m = _load(eval_path).get("metrics") or {}
    return {
        "all_rows": m.get("price_directional_hit_rate"),
        "dir_only": m.get("price_hit_rate_on_directional_calls"),
        "n": m.get("n_evaluated"),
        "calls": m.get("n_directional_calls"),
        "neutral": m.get("n_neutral_predictions"),
        "scoring_mode": m.get("scoring_mode"),
    }


def _run_lane(
    *,
    rule_id: str,
    dates: list[str],
    v1_map: dict[str, str],
    ms_map: dict[str, str],
    merge_fn: Callable[[str, str], str],
    py: str,
) -> dict[str, Any]:
    lane_work = WORK / rule_id
    lane_work.mkdir(parents=True, exist_ok=True)
    per_date = lane_work / "per_date.json"
    score = lane_work / "score.json"
    ev = lane_work / "eval.json"

    doc = {
        "schema": "btrack_ensemble_per_date_directions_v1",
        "version": "1.0.0",
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "ts_utc": _utc(),
        "ensemble_mode": f"hybrid_{rule_id}_v1",
        "research_only": True,
        "hybrid_rule": rule_id,
        "rows": build_hybrid_rows(
            dates=dates, v1_map=v1_map, ms_map=ms_map, rule_id=rule_id, merge_fn=merge_fn
        ),
    }
    per_date.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lane_lock = lane_work / ".score_writer.lock"
    cmd_score = [
        py,
        "scripts/build_btrack_prophecy_score_from_ohlcv.py",
        "--btc-csv",
        _rel(BTC),
        "--hypothesis-json",
        _rel(HYP),
        "--batch-eval-dates-json",
        _rel(ANCHOR_DATES),
        "--per-date-direction-json",
        _rel(per_date),
        "--lock-file",
        _rel(lane_lock),
        "--output",
        _rel(score),
    ]
    cp = subprocess.run(cmd_score, cwd=str(ROOT), capture_output=True, text=True)
    if cp.returncode != 0:
        raise RuntimeError(f"{rule_id} score\n{cp.stderr or cp.stdout}")

    cmd_eval = [
        py,
        "scripts/eval_prophecy_hit_rate_v1.py",
        "--run-mode",
        "price",
        "--score-json",
        _rel(score),
        "--headline-instrument",
        "btc",
        "--output",
        _rel(ev),
    ]
    cp = subprocess.run(cmd_eval, cwd=str(ROOT), capture_output=True, text=True)
    if cp.returncode != 0:
        raise RuntimeError(f"{rule_id} eval\n{cp.stderr or cp.stdout}")

    return {
        "rule_id": rule_id,
        "description": HYBRID_RULES[rule_id][0],
        "paths": {
            "per_date": _rel(per_date),
            "score": _rel(score),
            "eval": _rel(ev),
        },
        "metrics": _eval_metrics(ev),
    }


def _write_shadow_from_v1_eval() -> dict[str, Any]:
    src = ROOT / "reports/prophecy_hit_rate_eval_v1_prod_perdate_30d_v1.json"
    if not src.is_file():
        return {"written": False, "reason": "missing_v1_prod_eval"}
    doc = _load(src)
    doc["shadow_headline"] = {
        "label": "v1_per_date_anchor_30d",
        "research_only": True,
        "does_not_replace": "prophecy_hit_rate_eval_30d_frozen_kpi_a_v1",
        "copied_from": _rel(src),
        "copied_at_utc": _utc(),
    }
    SHADOW_EVAL.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"written": True, "path": _rel(SHADOW_EVAL)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--max-workers", type=int, default=5)
    ap.add_argument("--output", type=Path, default=OUT)
    ap.add_argument("--skip-shadow", action="store_true")
    args = ap.parse_args()

    for p in (ANCHOR_SCORE, ANCHOR_DATES, V1_PER_DATE, MS_PER_DATE, HYP, BTC):
        if not p.is_file():
            print(f"MISSING: {p}", file=sys.stderr)
            return 1

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
    v1_map = _dir_map(_load(V1_PER_DATE))
    ms_map = _dir_map(_load(MS_PER_DATE))
    py = sys.executable

    lanes: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max(1, args.max_workers)) as pool:
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

    shadow = {} if args.skip_shadow else _write_shadow_from_v1_eval()

    pack = {
        "schema": "btrack_v1_ms_hybrid_parallel_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "panel": {
            "n_days": len(dates),
            "anchor_dates": _rel(ANCHOR_DATES),
            "v1_per_date": _rel(V1_PER_DATE),
            "ms_per_date": _rel(MS_PER_DATE),
        },
        "baseline_reference": {
            "frozen_kpi_a_all_rows": 0.433333,
            "v1_per_date_all_rows": 0.566667,
            "ms_dir_only_on_13_calls": 0.692308,
            "matched_ms_active_v1": 0.615385,
        },
        "lanes": lanes,
        "best_all_rows_lane": best.get("rule_id") if best else None,
        "shadow_headline": shadow,
        "operator_lines": [
            "- [MKM-HYBRID-P] Parallel hybrid rules on anchor 30d; no Track A promotion.",
            "- [MKM-HYBRID-P] Compare best_all_rows_lane vs v1-only before human review.",
            "- [MKM-HYBRID-P] MS-active fair compare: reports/btrack_active_day_matched_compare_v1_latest.json",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    if best:
        m = best.get("metrics") or {}
        print(
            f"BEST all-rows: {best.get('rule_id')} "
            f"{m.get('all_rows')} dir={m.get('dir_only')} calls={m.get('calls')}"
        )
    return 0 if all(not lane.get("error") for lane in lanes) else 2


if __name__ == "__main__":
    raise SystemExit(main())
