#!/usr/bin/env python3
"""[HYPO] Bundle v9: KPI tiebreaker on MS-neutral conflicts + stacked hybrid variants."""
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

DEFAULT_OUT = ROOT / "reports/btrack_frozen30d_parallel_bundle_v9_latest.json"
WORK = ROOT / "reports/btrack_frozen30d_parallel_bundle_v9_work"
ANCHOR_SCORE = ROOT / "reports/btrack_prophecy_score_30d_frozen_kpi_a_v1.json"
ANCHOR_DATES = ROOT / "reports/btrack_anchor_eval_dates_v1.json"
LEGACY_V1 = ROOT / "reports/btrack_ensemble_per_date_v1_prod_perdate_30d_v1.json"
M016_PER = ROOT / "reports/btrack_frozen30d_margin_fine_sweep_work/per_date_margin_016.json"
MS_PER = ROOT / "reports/btrack_lens_combo_ms_per_date_anchor_v1.json"
DAILY_DIFF = ROOT / "reports/btrack_frozen30d_hybrid_daily_diff_v1_latest.json"
BTC = ROOT / "research/market_data/btc_daily_external_yf.csv"
HYP = ROOT / "docs/final/artifacts/btrack_hypothesis_prophecy_latest.json"
REC_CHAIN = ROOT / "scripts/run_prophecy_btrack_recommended_eval_chain_v1.py"

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


def _dir_map(doc: dict[str, Any], key: str = "predicted_direction") -> dict[str, str]:
    out: dict[str, str] = {}
    for row in doc.get("rows") or []:
        if not isinstance(row, dict):
            continue
        if str(row.get("instrument") or "btc").lower() != "btc":
            continue
        ed = str(row.get("eval_date") or "")[:10]
        if ed:
            out[ed] = str(row.get(key) or "neutral").strip().lower()
    return out


def _anchor_dates() -> list[str]:
    if ANCHOR_DATES.is_file():
        d = list(_load(ANCHOR_DATES).get("eval_dates") or [])
        if d:
            return sorted(str(x)[:10] for x in d)
    return sorted(_dir_map(_load(ANCHOR_SCORE)).keys())


def _run(cmd: list[str]) -> None:
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)}\n{p.stderr or p.stdout}")


def _bbs_v1(legacy: str, m016: str) -> str:
    if legacy == "bull" and m016 == "bear":
        return legacy
    return m016


def _is_dir(d: str) -> bool:
    return d in ("bull", "bear")


def _merge_agree_or_ms_else_v1(v1: str, ms: str) -> str:
    if _is_dir(v1) and v1 == ms:
        return v1
    if _is_dir(ms):
        return ms
    return v1 if _is_dir(v1) else "neutral"


def _hybrid_pred(
    legacy: str,
    m016: str,
    ms: str,
    kpi: str,
    *,
    mode: str,
) -> str:
    v1r = _bbs_v1(legacy, m016)
    if mode == "bbs_ms_agree":
        pred = _merge_agree_or_ms_else_v1(v1r, ms)
    elif mode == "bbs_ms_kpi_tb":
        pred = _merge_agree_or_ms_else_v1(v1r, ms)
        if pred == "bull" and ms == "neutral" and kpi == "bear":
            pred = "bear"
    elif mode == "bbs_ms_kpi_tb_bear_only":
        pred = _merge_agree_or_ms_else_v1(v1r, ms)
        if pred == "bull" and ms == "neutral" and kpi == "bear" and v1r == "bull":
            pred = "bear"
    elif mode == "bbs_ms_neutral_if_kpi_disagree":
        pred = _merge_agree_or_ms_else_v1(v1r, ms)
        if ms == "neutral" and _is_dir(kpi) and pred != kpi:
            pred = "neutral"
    else:
        raise ValueError(mode)
    return pred


def _simulate_all_modes() -> dict[str, Any]:
    diff = {
        str(d["eval_date"])[:10]: d
        for d in (_load(DAILY_DIFF).get("per_day") or [])
        if isinstance(d, dict)
    }
    kpi_map = _dir_map(_load(ANCHOR_SCORE))
    modes = ("bbs_ms_agree", "bbs_ms_kpi_tb", "bbs_ms_kpi_tb_bear_only", "bbs_ms_neutral_if_kpi_disagree")
    out: dict[str, Any] = {}
    for mode in modes:
        bucket = {"full": [0, 0], "h7": [0, 0], "train": [0, 0]}
        overrides: list[str] = []
        for ed, d in diff.items():
            leg = str(d.get("legacy_v1") or "").lower()
            m16 = str(d.get("m016_v1") or "").lower()
            ms = str(d.get("legacy_ms") or d.get("m016_ms") or "neutral").lower()
            kpi = kpi_map.get(ed, "neutral")
            base = _merge_agree_or_ms_else_v1(_bbs_v1(leg, m16), ms)
            pred = _hybrid_pred(leg, m16, ms, kpi, mode=mode)
            if pred != base:
                overrides.append(ed)
            act = str(d.get("actual") or "").lower()
            if pred not in ("bull", "bear") or act not in ("bull", "bear"):
                continue
            hit = int(pred == act)
            bucket["full"][0] += hit
            bucket["full"][1] += 1
            key = "h7" if ed in HOLDOUT7 else "train"
            bucket[key][0] += hit
            bucket[key][1] += 1
        out[mode] = {
            "override_dates": overrides,
            "full_30d": _rate(bucket["full"]),
            "holdout7": _rate(bucket["h7"]),
            "train23": _rate(bucket["train"]),
        }
    return out


def _rate(pair: list[int]) -> dict[str, Any]:
    h, n = pair
    return {"price_hits": h, "n_evaluated": n, "price_directional_hit_rate": round(h / n, 6) if n else None}


def _build_hybrid_per_date(mode: str, out: Path) -> dict[str, Any]:
    legacy_map = _dir_map(_load(LEGACY_V1))
    m016_map = _dir_map(_load(M016_PER))
    ms_map = _dir_map(_load(MS_PER))
    kpi_map = _dir_map(_load(ANCHOR_SCORE))
    dates = _anchor_dates()

    rows: list[dict[str, Any]] = []
    n_tb = 0
    for ed in dates:
        leg = legacy_map.get(ed, "neutral")
        m16 = m016_map.get(ed, "neutral")
        ms = ms_map.get(ed, "neutral")
        kpi = kpi_map.get(ed, "neutral")
        v1r = _bbs_v1(leg, m16)
        pred = _hybrid_pred(leg, m16, ms, kpi, mode=mode)
        base = _merge_agree_or_ms_else_v1(v1r, ms)
        if pred != base:
            n_tb += 1
        rows.append(
            {
                "eval_date": ed,
                "instrument": "btc",
                "predicted_direction": pred,
                "ensemble_mode": f"hybrid_{mode}_v1",
                "hybrid_rule": mode,
                "sources": {"v1": v1r, "ms": ms, "kpi_anchor": kpi, "legacy_v1": leg, "m016_v1": m16},
            }
        )

    doc = {
        "schema": "btrack_ensemble_per_date_directions_v1",
        "version": "1.0.0",
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "ts_utc": _utc(),
        "ensemble_mode": f"hybrid_{mode}_v1",
        "research_only": True,
        "rows": rows,
        "meta": {"mode": mode, "kpi_tiebreaker_applied": n_tb},
    }
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"mode": mode, "kpi_tiebreaker_applied": n_tb, "path": str(out)}


def _score_eval(per_date: Path, slug: str) -> dict[str, Any]:
    sub = WORK / slug
    sub.mkdir(parents=True, exist_ok=True)
    dates_path = sub / "dates.json"
    dates_path.write_text(json.dumps({"eval_dates": _anchor_dates()}, indent=2) + "\n", encoding="utf-8")
    score = sub / "score.json"
    ev = sub / "eval.json"
    lock = sub / ".lock"
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
    m = (_load(ev).get("metrics") or {}) if ev.is_file() else {}
    sliced = _slice_from_score(score)
    return {**m, **{"slices": sliced}}


def _slice_from_score(score_path: Path) -> dict[str, Any]:
    rows = [
        r
        for r in (_load(score_path).get("rows") or [])
        if isinstance(r, dict) and str(r.get("instrument") or "").lower() == "btc"
    ]

    def _agg(edset: set[str]) -> dict[str, Any]:
        h = n = 0
        for r in rows:
            ed = str(r.get("eval_date") or "")[:10]
            if ed not in edset:
                continue
            pred = str(r.get("predicted_direction") or "").lower()
            act = str(r.get("actual_direction") or "").lower()
            if pred in ("bull", "bear") and act in ("bull", "bear"):
                n += 1
                h += int(pred == act)
        return {"n_evaluated": n, "price_hits": h, "price_directional_hit_rate": round(h / n, 6) if n else None}

    all_ed = {str(r.get("eval_date") or "")[:10] for r in rows}
    return {
        "full_30d": _agg(all_ed),
        "holdout7": _agg(set(HOLDOUT7) & all_ed),
        "train23": _agg(all_ed - HOLDOUT7),
    }


def _task_simulation() -> dict[str, Any]:
    rules = _simulate_all_modes()
    out = ROOT / "reports/btrack_frozen30d_kpi_tiebreaker_sim_v1_latest.json"
    out.write_text(
        json.dumps(
            {
                "schema": "btrack_frozen30d_kpi_tiebreaker_sim_v1",
                "generated_at_utc": _utc(),
                "research_only": True,
                "rules": rules,
                "note": "kpi_tb uses frozen KPI-A score direction when hybrid bull + MS neutral + KPI bear.",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return {"task": "kpi_tiebreaker_sim", "exit_code": 0, "summary": rules}


def _task_pipeline_kpi_tb() -> dict[str, Any]:
    per = WORK / "per_date_bbs_ms_kpi_tb.json"
    meta = _build_hybrid_per_date("bbs_ms_kpi_tb", per)
    metrics = _score_eval(per, "bbs_ms_kpi_tb")
    return {"task": "pipeline_bbs_ms_kpi_tb", "exit_code": 0, "summary": {**meta, **metrics}}


def _task_promotion_kpi_tb() -> dict[str, Any]:
    per = WORK / "per_date_bbs_ms_kpi_tb.json"
    if not per.is_file():
        return {"task": "promotion_kpi_tb", "exit_code": 2, "error": "run pipeline first"}
    gates_out = WORK / "promotion_gates_kpi_tb.json"
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
            str(WORK / "chain_summary_kpi_tb.json"),
            "--calibration-note",
            "bbs_ms_kpi_tiebreaker_v9",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    g = _load(gates_out) if gates_out.is_file() else {}
    return {
        "task": "promotion_kpi_tb",
        "exit_code": proc.returncode,
        "summary": {
            "combined_all_passed": bool(g.get("combined_all_passed")),
            "outcome_class": g.get("outcome_class"),
        },
    }


def _task_update_manifest() -> dict[str, Any]:
    manifest_path = ROOT / "reports/btrack_bbs_ms_hybrid_candidate_manifest_v1_latest.json"
    sim_path = ROOT / "reports/btrack_frozen30d_kpi_tiebreaker_sim_v1_latest.json"
    if not manifest_path.is_file():
        return {"task": "update_manifest", "exit_code": 2, "error": "missing manifest"}
    m = _load(manifest_path)
    sim = _load(sim_path) if sim_path.is_file() else {}
    kpi_tb = (sim.get("rules") or {}).get("bbs_ms_kpi_tb") or {}
    m["variant_kpi_tiebreaker"] = {
        "rule": "hybrid bull + MS neutral + frozen_kpi bear → use bear (KPI direction)",
        "metrics_frozen_30d": kpi_tb.get("full_30d"),
        "metrics_holdout7": kpi_tb.get("holdout7"),
        "caveat": "Uses frozen KPI-A lane direction as tiebreaker — research coupling; not independent OOS.",
    }
    m["generated_at_utc"] = _utc()
    manifest_path.write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"task": "update_manifest", "exit_code": 0, "summary": m.get("variant_kpi_tiebreaker")}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    WORK.mkdir(parents=True, exist_ok=True)

    results: list[dict[str, Any]] = [ _task_simulation() ]

    with ThreadPoolExecutor(max_workers=3) as pool:
        futs = [
            pool.submit(_task_pipeline_kpi_tb),
            pool.submit(_task_update_manifest),
        ]
        for fut in as_completed(futs):
            try:
                results.append(fut.result())
            except Exception as exc:
                results.append({"task": "parallel", "exit_code": 2, "error": str(exc)})

    try:
        results.append(_task_promotion_kpi_tb())
    except Exception as exc:
        results.append({"task": "promotion_kpi_tb", "exit_code": 2, "error": str(exc)})

    bundle = {
        "schema": "btrack_frozen30d_parallel_bundle_v9",
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
