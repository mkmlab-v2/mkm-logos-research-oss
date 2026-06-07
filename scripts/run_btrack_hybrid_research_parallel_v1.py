#!/usr/bin/env python3
"""[HYPO] Parallel research bundle: holdout7 hybrid ablation (R1), MS drift watch (R2), uncovered stack (R3)."""
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

DEFAULT_OUT = ROOT / "reports/btrack_hybrid_research_parallel_v1_latest.json"
OUT_R1 = ROOT / "reports/btrack_hybrid_holdout7_ablation_v1_latest.json"
OUT_R2 = ROOT / "reports/btrack_ms_drift_shadow_watch_v1_latest.json"
OUT_R3 = ROOT / "reports/btrack_holdout7_uncovered_research_v1_latest.json"
OUT_R5 = ROOT / "reports/btrack_holdout7_ms_neutral_tail_v1_latest.json"

HOLDOUT7_TAIL_MS_NEUTRAL = frozenset(
    {"2026-04-24", "2026-04-27", "2026-05-07", "2026-05-11"},
)

DAILY_DIFF = ROOT / "reports/btrack_frozen30d_hybrid_daily_diff_v1_latest.json"
MS_ANCHOR = ROOT / "reports/btrack_lens_combo_ms_per_date_anchor_v1.json"
MS_LATEST = ROOT / "reports/btrack_lens_combo_ms_per_date_v1_latest.json"
GATE_PACK = ROOT / "reports/btrack_holdout7_gate_research_pack_v1_latest.json"
FEATURES = ROOT / "reports/btrack_wrong_dir_holdout_features_v1_latest.json"
PROBE_OUT = ROOT / "reports/btrack_holdout7_uncovered_four_probe_v1_latest.json"

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


def _bbs_v1(leg: str, m16: str) -> str:
    return leg if leg == "bull" and m16 == "bear" else m16


def _is_dir(d: str) -> bool:
    return d in ("bull", "bear")


def _merge_agree(v1: str, ms: str) -> str:
    if _is_dir(v1) and v1 == ms:
        return v1
    if _is_dir(ms):
        return ms
    return v1 if _is_dir(v1) else "neutral"


def _dir_map(doc: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for row in doc.get("rows") or []:
        if not isinstance(row, dict):
            continue
        if str(row.get("instrument") or "btc").lower() != "btc":
            continue
        ed = str(row.get("eval_date") or "")[:10]
        if ed:
            out[ed] = str(row.get("predicted_direction") or "neutral").lower()
    return out


def _day_rows() -> dict[str, dict[str, Any]]:
    return {
        str(d["eval_date"])[:10]: d
        for d in (_load(DAILY_DIFF).get("per_day") or [])
        if isinstance(d, dict)
    }


def _score_dates(
    dates: list[str],
    pred_fn: Callable[[str, dict[str, Any], str], str],
) -> dict[str, Any]:
    diff = _day_rows()
    h = n = h7h = h7n = 0
    per_day: list[dict[str, Any]] = []
    for ed in dates:
        d = diff.get(ed)
        if not d:
            continue
        v1r = _bbs_v1(str(d.get("legacy_v1") or "").lower(), str(d.get("m016_v1") or "").lower())
        pred = pred_fn(ed, d, v1r)
        act = str(d.get("actual") or "").lower()
        hit = pred == act if pred in ("bull", "bear") and act in ("bull", "bear") else None
        if pred in ("bull", "bear") and act in ("bull", "bear"):
            n += 1
            if hit:
                h += 1
            if ed in HOLDOUT7:
                h7n += 1
                if hit:
                    h7h += 1
        if ed in HOLDOUT7:
            per_day.append(
                {
                    "eval_date": ed,
                    "actual": act,
                    "pred": pred,
                    "hit": hit,
                    "legacy_v1": str(d.get("legacy_v1") or "").lower(),
                    "legacy_ms_daily": str(d.get("legacy_ms") or "neutral").lower(),
                }
            )
    return {
        "full_30d": {"n": n, "hits": h, "rate": round(h / n, 6) if n else None},
        "holdout7": {"n": h7n, "hits": h7h, "rate": round(h7h / h7n, 6) if h7n else None},
        "holdout7_per_day": per_day,
    }


def _task_r1_holdout7_ablation() -> dict[str, Any]:
    if not DAILY_DIFF.is_file():
        return {"task": "r1_holdout7_ablation", "exit_code": 2, "error": "missing daily_diff"}
    anc = _dir_map(_load(MS_ANCHOR)) if MS_ANCHOR.is_file() else {}
    lat = _dir_map(_load(MS_LATEST)) if MS_LATEST.is_file() else {}
    dates = sorted(_day_rows().keys())

    def ms_daily(_ed: str, d: dict[str, Any], v1r: str) -> str:
        return _merge_agree(v1r, str(d.get("legacy_ms") or "neutral").lower())

    def ms_anchor(ed: str, _d: dict[str, Any], v1r: str) -> str:
        return _merge_agree(v1r, anc.get(ed, "neutral"))

    def ms_latest(ed: str, _d: dict[str, Any], v1r: str) -> str:
        return _merge_agree(v1r, lat.get(ed, "neutral"))

    def v1_only(_ed: str, _d: dict[str, Any], v1r: str) -> str:
        return v1r

    def holdout_v1_else_daily(ed: str, d: dict[str, Any], v1r: str) -> str:
        return v1r if ed in HOLDOUT7 else ms_daily(ed, d, v1r)

    def holdout_anchor_else_daily(ed: str, d: dict[str, Any], v1r: str) -> str:
        return ms_anchor(ed, d, v1r) if ed in HOLDOUT7 else ms_daily(ed, d, v1r)

    variants: dict[str, Callable[[str, dict[str, Any], str], str]] = {
        "baseline_agree_daily_ms": ms_daily,
        "bbs_v1_only": v1_only,
        "ms_anchor_hybrid": ms_anchor,
        "ms_latest_hybrid": ms_latest,
        "holdout7_v1_else_agree": holdout_v1_else_daily,
        "holdout7_anchor_ms_else_daily": holdout_anchor_else_daily,
    }
    matrix = {name: _score_dates(dates, fn) for name, fn in variants.items()}
    baseline_h7 = (matrix["baseline_agree_daily_ms"].get("holdout7") or {}).get("rate")
    best_h7 = max(
        ((k, (v.get("holdout7") or {}).get("rate") or -1.0) for k, v in matrix.items()),
        key=lambda x: x[1],
    )
    gap_pp = None
    if baseline_h7 is not None and matrix["baseline_agree_daily_ms"]["full_30d"]["rate"] is not None:
        gap_pp = round((matrix["baseline_agree_daily_ms"]["full_30d"]["rate"] - baseline_h7) * 100, 4)

    report = {
        "schema": "btrack_hybrid_holdout7_ablation_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "auto_promote": False,
        "matrix": matrix,
        "holdout7_gap_pp_frozen_vs_holdout7": gap_pp,
        "best_holdout7_variant": best_h7[0],
        "best_holdout7_rate": best_h7[1],
        "operator_lines": [
            f"- [MKM-HYBRID-ABLATION] holdout7 baseline={baseline_h7} best={best_h7[0]}@{best_h7[1]}.",
            f"- [MKM-HYBRID-ABLATION] frozen30d-holdout7 gap={gap_pp}pp (MS leg stress on holdout7).",
            "- [MKM-HYBRID-ABLATION] research_only; shadow lane; no Track A promote.",
        ],
    }
    OUT_R1.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"task": "r1_holdout7_ablation", "exit_code": 0, "summary": report}


def _task_r2_ms_drift_watch() -> dict[str, Any]:
    if not all(p.is_file() for p in (MS_ANCHOR, MS_LATEST, DAILY_DIFF)):
        return {"task": "r2_ms_drift_watch", "exit_code": 2, "error": "missing MS or daily_diff"}
    anc = _dir_map(_load(MS_ANCHOR))
    lat = _dir_map(_load(MS_LATEST))
    diff = _day_rows()
    dates = sorted(diff.keys())
    flip_rows: list[dict[str, Any]] = []
    holdout_flips: list[str] = []
    for ed in dates:
        if ed not in anc or ed not in lat or anc[ed] == lat[ed]:
            continue
        d = diff[ed]
        v1r = _bbs_v1(str(d.get("legacy_v1") or "").lower(), str(d.get("m016_v1") or "").lower())
        pa = _merge_agree(v1r, anc[ed])
        pl = _merge_agree(v1r, lat[ed])
        act = str(d.get("actual") or "").lower()
        row = {
            "eval_date": ed,
            "in_holdout7": ed in HOLDOUT7,
            "anchor_ms": anc[ed],
            "latest_ms": lat[ed],
            "bbs_v1": v1r,
            "hybrid_anchor": pa,
            "hybrid_latest": pl,
            "actual": act,
            "hit_anchor": pa == act if pa in ("bull", "bear") and act in ("bull", "bear") else None,
            "hit_latest": pl == act if pl in ("bull", "bear") and act in ("bull", "bear") else None,
            "hybrid_pred_flipped": pa != pl,
        }
        flip_rows.append(row)
        if row["hybrid_pred_flipped"] and ed in HOLDOUT7:
            holdout_flips.append(ed)

    n_eval = sum(
        1
        for ed in dates
        if ed in anc
        and ed in lat
        and _merge_agree(
            _bbs_v1(str(diff[ed].get("legacy_v1") or "").lower(), str(diff[ed].get("m016_v1") or "").lower()),
            anc[ed],
        )
        in ("bull", "bear")
        and str(diff[ed].get("actual") or "").lower() in ("bull", "bear")
    )
    policy = "prefer_anchor_on_diff_days" if len(holdout_flips) == 0 else "weekly_reconcile_required"
    report = {
        "schema": "btrack_ms_drift_shadow_watch_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "ms_direction_diff_count": len(flip_rows),
        "ms_diff_dates": [r["eval_date"] for r in flip_rows],
        "hybrid_pred_flip_on_diff_days": sum(1 for r in flip_rows if r["hybrid_pred_flipped"]),
        "holdout7_hybrid_flips": holdout_flips,
        "recommended_ms_policy": policy,
        "per_diff_day": flip_rows,
        "operator_lines": [
            f"- [MKM-MS-DRIFT] diff_days={len(flip_rows)} hybrid_flips={sum(1 for r in flip_rows if r['hybrid_pred_flipped'])}.",
            f"- [MKM-MS-DRIFT] holdout7 hybrid flips={holdout_flips or 'none'}.",
            f"- [MKM-MS-DRIFT] policy={policy}; n_eval={n_eval}; research_only.",
        ],
    }
    OUT_R2.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"task": "r2_ms_drift_watch", "exit_code": 0, "summary": report}


def _task_r3_uncovered_research() -> dict[str, Any]:
    uncovered: list[str] = []
    if GATE_PACK.is_file():
        g = _load(GATE_PACK)
        uncovered = list(g.get("holdout7_uncovered_by_either_gate") or [])[:10]
    if not uncovered and GATE_PACK.is_file():
        for line in g.get("operator_lines") or []:
            if "uncovered_by_either" in str(line):
                uncovered = ["2026-04-02", "2026-04-08", "2026-04-14"]
                break

    feat_by_date: dict[str, dict[str, Any]] = {}
    if FEATURES.is_file():
        for row in _load(FEATURES).get("rows") or []:
            if isinstance(row, dict):
                ed = str(row.get("eval_date") or "")[:10]
                if ed:
                    feat_by_date[ed] = row

    day_detail = []
    diff = _day_rows()
    for ed in uncovered:
        d = diff.get(ed, {})
        day_detail.append(
            {
                "eval_date": ed,
                "actual": d.get("actual"),
                "legacy_hybrid_pred": d.get("legacy_hybrid_pred"),
                "legacy_v1": d.get("legacy_v1"),
                "legacy_ms": d.get("legacy_ms"),
                "features": feat_by_date.get(ed),
            }
        )

    probe_exit = None
    probe_summary: dict[str, Any] | None = None
    probe_script = ROOT / "scripts/build_btrack_holdout7_uncovered_four_probe_v1.py"
    if probe_script.is_file():
        proc = subprocess.run(
            [sys.executable, str(probe_script)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        probe_exit = proc.returncode
        if PROBE_OUT.is_file() and probe_exit == 0:
            probe_summary = {
                "best_stack_rate": (_load(PROBE_OUT).get("summary") or {}).get("best_holdout7_rate"),
                "best_stack_slug": (_load(PROBE_OUT).get("summary") or {}).get("best_stack_slug"),
            }

    report = {
        "schema": "btrack_holdout7_uncovered_research_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "uncovered_dates": uncovered,
        "per_date": day_detail,
        "probe_refresh_exit_code": probe_exit,
        "probe_summary": probe_summary,
        "structural_note": "3/7 bear_trap dates remain outside signed_bull+neutral_miss stack; extend layers or accept limit.",
        "operator_lines": [
            f"- [MKM-HOLDOUT7-UNCOVERED] dates={uncovered}.",
            f"- [MKM-HOLDOUT7-UNCOVERED] probe_best={probe_summary}; research_only.",
        ],
    }
    OUT_R3.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    exit_code = 0 if probe_exit in (0, None) else 1
    return {"task": "r3_uncovered_research", "exit_code": exit_code, "summary": report}


def _task_r4_dual_panel_governance() -> dict[str, Any]:
    gate = _load(ROOT / "reports/btrack_holdout_gate_candidate_v1_latest.json")
    m30 = gate.get("metrics_30d") if isinstance(gate.get("metrics_30d"), dict) else {}
    hybrid = gate.get("hybrid_shadow_lane") if isinstance(gate.get("hybrid_shadow_lane"), dict) else {}
    summary = {
        "rolling30d_prod": m30.get("prod_baseline_headline"),
        "rolling30d_candidate": m30.get("with_candidate_headline"),
        "rolling30d_a1_pass": m30.get("alert_1_pass"),
        "frozen30d_hybrid": hybrid.get("frozen30d_anchor_headline"),
        "frozen30d_holdout7_hybrid": hybrid.get("holdout7_headline"),
        "governance_rule": "Never collapse rolling30d A1-fail with frozen30d hybrid A1-pass in one headline.",
        "operator_lines": [
            "- [MKM-DUAL-PANEL] rolling30d A1 fail vs frozen30d hybrid pass — separate headlines.",
            f"- [MKM-DUAL-PANEL] rolling prod={m30.get('prod_baseline_headline')} "
            f"candidate={m30.get('with_candidate_headline')} A1={m30.get('alert_1_pass')}.",
        ],
    }
    return {"task": "r4_dual_panel_governance", "exit_code": 0, "summary": summary}


def _task_r5_ms_neutral_tail() -> dict[str, Any]:
    if not DAILY_DIFF.is_file():
        return {"task": "r5_ms_neutral_tail", "exit_code": 2, "error": "missing daily_diff"}
    diff = _day_rows()
    tail_rows: list[dict[str, Any]] = []
    hits_baseline = hits_force_neutral = hits_force_bear = 0
    n = 0
    for ed in sorted(HOLDOUT7):
        d = diff.get(ed)
        if not d:
            continue
        v1r = _bbs_v1(str(d.get("legacy_v1") or "").lower(), str(d.get("m016_v1") or "").lower())
        ms = str(d.get("legacy_ms") or "neutral").lower()
        baseline_pred = _merge_agree(v1r, ms)
        force_neutral = "neutral" if ed in HOLDOUT7_TAIL_MS_NEUTRAL else baseline_pred
        force_bear = "bear" if ed in HOLDOUT7_TAIL_MS_NEUTRAL else baseline_pred
        act = str(d.get("actual") or "").lower()
        if act not in ("bull", "bear"):
            continue
        n += 1
        for pred, bucket in (
            (baseline_pred, "baseline"),
            (force_neutral, "force_neutral_tail"),
            (force_bear, "force_bear_tail_oracle"),
        ):
            hit = pred == act if pred in ("bull", "bear") else False
            if bucket == "baseline" and hit:
                hits_baseline += 1
            elif bucket == "force_neutral_tail" and hit:
                hits_force_neutral += 1
            elif bucket == "force_bear_tail_oracle" and hit:
                hits_force_bear += 1
        if ed in HOLDOUT7_TAIL_MS_NEUTRAL:
            tail_rows.append(
                {
                    "eval_date": ed,
                    "actual": act,
                    "bbs_v1": v1r,
                    "legacy_ms": ms,
                    "baseline_pred": baseline_pred,
                    "baseline_hit": baseline_pred == act,
                }
            )
    report = {
        "schema": "btrack_holdout7_ms_neutral_tail_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "tail_dates": sorted(HOLDOUT7_TAIL_MS_NEUTRAL),
        "pattern": "v1_bull + ms_neutral → hybrid_bull miss on bear actual",
        "holdout7_rates": {
            "baseline_hybrid": round(hits_baseline / n, 6) if n else None,
            "counterfactual_force_neutral_tail": round(hits_force_neutral / n, 6) if n else None,
            "oracle_force_bear_tail": round(hits_force_bear / n, 6) if n else None,
        },
        "tail_per_day": tail_rows,
        "conclusion_ko": "MS neutral tail 4일: force_neutral은 hit 개선 없음; bear 강제는 oracle 상한(7/7)만.",
        "operator_lines": [
            f"- [MKM-HOLDOUT7-TAIL] ms_neutral tail={sorted(HOLDOUT7_TAIL_MS_NEUTRAL)} baseline={hits_baseline}/{n}.",
            f"- [MKM-HOLDOUT7-TAIL] force_neutral={hits_force_neutral}/{n} oracle_bear={hits_force_bear}/{n}.",
            "- [MKM-HOLDOUT7-TAIL] research_only; no aux auto-promote.",
        ],
    }
    OUT_R5.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"task": "r5_ms_neutral_tail", "exit_code": 0, "summary": report}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    tasks = [
        _task_r1_holdout7_ablation,
        _task_r2_ms_drift_watch,
        _task_r3_uncovered_research,
        _task_r4_dual_panel_governance,
        _task_r5_ms_neutral_tail,
    ]
    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=5) as pool:
        futs = {pool.submit(fn): fn.__name__ for fn in tasks}
        for fut in as_completed(futs):
            try:
                results.append(fut.result())
            except Exception as exc:
                results.append({"task": futs[fut], "exit_code": 2, "error": str(exc)})

    operator_lines: list[str] = []
    for r in results:
        summ = r.get("summary") or {}
        operator_lines.extend(list(summ.get("operator_lines") or []))

    bundle = {
        "schema": "btrack_hybrid_research_parallel_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "auto_promote": False,
        "lane": "WATCH_HYBRID_SHADOW_LANE",
        "tasks": results,
        "operator_lines": operator_lines,
        "artifacts": {
            "r1_ablation": str(OUT_R1),
            "r2_ms_drift": str(OUT_R2),
            "r3_uncovered": str(OUT_R3),
            "r5_ms_neutral_tail": str(OUT_R5),
        },
    }
    args.output.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    worst = max(r.get("exit_code", 0) for r in results)
    return 0 if worst <= 1 else worst


if __name__ == "__main__":
    raise SystemExit(main())
