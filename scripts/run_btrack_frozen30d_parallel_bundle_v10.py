#!/usr/bin/env python3
"""[HYPO] Bundle v10: train-miss autopsy, hybrid rule matrix, shadow lane pack, observation refresh."""
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

DEFAULT_OUT = ROOT / "reports/btrack_frozen30d_parallel_bundle_v10_latest.json"
WORK = ROOT / "reports/btrack_frozen30d_parallel_bundle_v10_work"
DAILY_DIFF = ROOT / "reports/btrack_frozen30d_hybrid_daily_diff_v1_latest.json"
HOLDOUT7_PANEL = ROOT / "reports/btrack_frozen30d_holdout7_scored_panel_v1_latest.json"
FEATURES = ROOT / "reports/btrack_wrong_dir_holdout_features_v1_latest.json"
ANCHOR_SCORE = ROOT / "reports/btrack_prophecy_score_30d_frozen_kpi_a_v1.json"
LEGACY_V1 = ROOT / "reports/btrack_ensemble_per_date_v1_prod_perdate_30d_v1.json"
M016_PER = ROOT / "reports/btrack_frozen30d_margin_fine_sweep_work/per_date_margin_016.json"
MS_ANCHOR = ROOT / "reports/btrack_lens_combo_ms_per_date_anchor_v1.json"
MS_LATEST = ROOT / "reports/btrack_lens_combo_ms_per_date_v1_latest.json"
BBS_HYBRID_PER = ROOT / "reports/btrack_frozen30d_parallel_bundle_v6_work/per_date_bull_bear_split_hybrid_hybrid.json"
if not BBS_HYBRID_PER.is_file():
    BBS_HYBRID_PER = ROOT / "reports/btrack_frozen30d_parallel_bundle_v6_work/per_date_bull_bear_split_hybrid.json"
MANIFEST = ROOT / "reports/btrack_bbs_ms_hybrid_candidate_manifest_v1_latest.json"

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


def _merge_ms_active(v1: str, ms: str) -> str:
    return ms if _is_dir(ms) else v1


def _rate_hits(dates: list[str], pred_fn) -> dict[str, Any]:
    diff = {
        str(d["eval_date"])[:10]: d
        for d in (_load(DAILY_DIFF).get("per_day") or [])
        if isinstance(d, dict)
    }
    h = n = h7h = h7n = 0
    for ed in dates:
        d = diff.get(ed)
        if not d:
            continue
        leg = str(d.get("legacy_v1") or "").lower()
        m16 = str(d.get("m016_v1") or "").lower()
        ms = str(d.get("legacy_ms") or "neutral").lower()
        v1r = _bbs_v1(leg, m16)
        pred = pred_fn(v1r, ms)
        act = str(d.get("actual") or "").lower()
        if pred not in ("bull", "bear") or act not in ("bull", "bear"):
            continue
        n += 1
        hit = pred == act
        if hit:
            h += 1
        if ed in HOLDOUT7:
            h7n += 1
            if hit:
                h7h += 1
    return {
        "full_30d": {"n": n, "hits": h, "rate": round(h / n, 6) if n else None},
        "holdout7": {"n": h7n, "hits": h7h, "rate": round(h7h / h7n, 6) if h7n else None},
    }


def _task_hybrid_rule_matrix() -> dict[str, Any]:
    dates = sorted(
        str(d["eval_date"])[:10]
        for d in (_load(DAILY_DIFF).get("per_day") or [])
        if isinstance(d, dict)
    )
    bbs_rules = {
        "bbs_ms_agree_or_ms_else": lambda v1, ms: _merge_agree(v1, ms),
        "bbs_ms_when_active_else_v1": lambda v1, ms: _merge_ms_active(v1, ms),
    }
    legacy_map = _dir_map(_load(LEGACY_V1))
    ms_map = _dir_map(_load(MS_ANCHOR))

    matrix: dict[str, Any] = {}
    for name, fn in bbs_rules.items():
        matrix[name] = _rate_hits(dates, fn)

    # legacy v1 + MS (no BBS)
    name = "legacy_v1_ms_agree"
    h = n = h7h = h7n = 0
    diff = {
        str(d["eval_date"])[:10]: d
        for d in (_load(DAILY_DIFF).get("per_day") or [])
        if isinstance(d, dict)
    }
    for ed in dates:
        d = diff[ed]
        v1 = legacy_map.get(ed, "neutral")
        ms = ms_map.get(ed, "neutral")
        pred = _merge_agree(v1, ms)
        act = str(d.get("actual") or "").lower()
        if pred not in ("bull", "bear") or act not in ("bull", "bear"):
            continue
        n += 1
        if pred == act:
            h += 1
        if ed in HOLDOUT7:
            h7n += 1
            if pred == act:
                h7h += 1
    matrix[name] = {
        "full_30d": {"n": n, "hits": h, "rate": round(h / n, 6) if n else None},
        "holdout7": {"n": h7n, "hits": h7h, "rate": round(h7h / h7n, 6) if h7n else None},
    }

    out = ROOT / "reports/btrack_frozen30d_hybrid_rule_matrix_v1_latest.json"
    report = {
        "schema": "btrack_frozen30d_hybrid_rule_matrix_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "matrix": matrix,
        "winner_full_30d": max(
            ((k, (v.get("full_30d") or {}).get("rate") or -1) for k, v in matrix.items()),
            key=lambda x: x[1],
        )[0],
    }
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"task": "hybrid_rule_matrix", "exit_code": 0, "summary": matrix}


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


def _m016_dir_map() -> dict[str, str]:
    if M016_PER.is_file():
        return _dir_map(_load(M016_PER))
    out: dict[str, str] = {}
    for d in _load(DAILY_DIFF).get("per_day") or []:
        if isinstance(d, dict):
            ed = str(d.get("eval_date") or "")[:10]
            if ed:
                out[ed] = str(d.get("m016_v1") or "neutral").lower()
    return out


def _task_train_miss_autopsy() -> dict[str, Any]:
    panel = _load(HOLDOUT7_PANEL)
    train_days = (panel.get("lanes") or {}).get("bbs_hybrid", {}).get("train23", {}).get("per_day") or []
    diff = {
        str(d["eval_date"])[:10]: d
        for d in (_load(DAILY_DIFF).get("per_day") or [])
        if isinstance(d, dict)
    }
    feat = {}
    if FEATURES.is_file():
        for row in _load(FEATURES).get("rows") or []:
            if isinstance(row, dict):
                ed = str(row.get("eval_date") or "")[:10]
                if ed:
                    feat[ed] = row
    kpi = _dir_map(_load(ANCHOR_SCORE))
    rows_out: list[dict[str, Any]] = []
    for day in train_days:
        if not isinstance(day, dict) or day.get("hit"):
            continue
        ed = str(day.get("eval_date") or "")[:10]
        d = diff.get(ed, {})
        rows_out.append(
            {
                "eval_date": ed,
                "actual": day.get("actual"),
                "bbs_hybrid_pred": day.get("pred"),
                "legacy_v1": d.get("legacy_v1"),
                "m016_v1": d.get("m016_v1"),
                "ms": d.get("legacy_ms"),
                "frozen_kpi": kpi.get(ed),
                "bbs_pattern": d.get("legacy_v1") == "bull" and d.get("m016_v1") == "bear",
                "miss_type": (
                    "false_bull"
                    if str(day.get("actual") or "") == "bear" and day.get("pred") == "bull"
                    else "false_bear"
                ),
                "prior_range_position": (feat.get(ed) or {}).get("prior_range_position"),
            }
        )

    out = ROOT / "reports/btrack_frozen30d_train_miss_autopsy_v1_latest.json"
    report = {
        "schema": "btrack_frozen30d_train_miss_autopsy_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "n_miss": len(rows_out),
        "false_bull": sum(1 for r in rows_out if r.get("miss_type") == "false_bull"),
        "false_bear": sum(1 for r in rows_out if r.get("miss_type") == "false_bear"),
        "bbs_pattern_hits": sum(1 for r in rows_out if r.get("bbs_pattern")),
        "rows": rows_out,
    }
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"task": "train_miss_autopsy", "exit_code": 0, "summary": report}


def _task_shadow_lane_pack() -> dict[str, Any]:
    manifest = _load(MANIFEST) if MANIFEST.is_file() else {}
    panel = _load(HOLDOUT7_PANEL) if HOLDOUT7_PANEL.is_file() else {}
    bbs = (panel.get("lanes") or {}).get("bbs_hybrid", {})

    pack = {
        "schema": "btrack_bbs_ms_hybrid_shadow_lane_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "operator_recommendation": "shadow_only_not_headline",
        "lane_id": "bbs_ms_hybrid_frozen30d_v1",
        "candidate_manifest": str(MANIFEST.relative_to(ROOT)).replace("\\", "/"),
        "per_date_path": str(BBS_HYBRID_PER.relative_to(ROOT)).replace("\\", "/"),
        "metrics": {
            "frozen_30d_all_rows": (bbs.get("full_30d") or {}).get("price_directional_hit_rate"),
            "holdout7": (bbs.get("holdout7") or {}).get("price_directional_hit_rate"),
            "frozen_kpi_a_baseline": 0.433333,
            "delta_pp": manifest.get("metrics_frozen_30d_btc", {}).get("delta_vs_kpi_a_pp"),
        },
        "gates": manifest.get("gates") or {"combined_all_passed": False},
        "do_not": [
            "replace_frozen_kpi_a_headline",
            "auto_promote_track_a",
            "use_kpi_tiebreaker_for_holdout7",
        ],
        "refresh_commands": [
            "py scripts/run_btrack_frozen30d_parallel_bundle_v6.py",
            "py scripts/run_btrack_frozen30d_parallel_bundle_v7.py",
            "py scripts/run_btrack_frozen30d_parallel_bundle_v8.py",
        ],
    }
    out = ROOT / "reports/btrack_bbs_ms_hybrid_shadow_lane_v1_latest.json"
    out.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"task": "shadow_lane_pack", "exit_code": 0, "summary": pack["metrics"]}


def _task_observation_refresh() -> dict[str, Any]:
    proc = subprocess.run(
        [sys.executable, "scripts/build_btrack_prophecy_observation_mode_status_v1.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    obs_path = ROOT / "reports/btrack_prophecy_observation_mode_status_v1_latest.json"
    obs = _load(obs_path) if obs_path.is_file() else {}
    # Append shadow lane pointer (non-destructive sidecar)
    sidecar = ROOT / "reports/btrack_prophecy_observation_bbs_shadow_pointer_v1_latest.json"
    sidecar.write_text(
        json.dumps(
            {
                "schema": "btrack_prophecy_observation_bbs_shadow_pointer_v1",
                "generated_at_utc": _utc(),
                "shadow_lane": "reports/btrack_bbs_ms_hybrid_shadow_lane_v1_latest.json",
                "manifest": "reports/btrack_bbs_ms_hybrid_candidate_manifest_v1_latest.json",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "task": "observation_refresh",
        "exit_code": proc.returncode,
        "summary": {"observation_ok": proc.returncode == 0, "sidecar": str(sidecar)},
        "stderr_tail": (proc.stderr or "")[-300:] if proc.returncode else None,
    }


def _task_ms_anchor_vs_latest() -> dict[str, Any]:
    if not MS_LATEST.is_file() or not MS_ANCHOR.is_file():
        return {"task": "ms_anchor_vs_latest", "exit_code": 2, "error": "missing MS per_date"}
    dates = _anchor_dates_list()
    anc = _dir_map(_load(MS_ANCHOR))
    lat = _dir_map(_load(MS_LATEST))
    leg = _dir_map(_load(LEGACY_V1))
    m16 = _m016_dir_map()
    agree_anc = agree_lat = n = 0
    ms_diff_days: list[str] = []
    for ed in dates:
        if ed not in anc or ed not in lat:
            continue
        v1r = _bbs_v1(leg.get(ed, "neutral"), m16.get(ed, "neutral"))
        pa = _merge_agree(v1r, anc[ed])
        pl = _merge_agree(v1r, lat[ed])
        if anc[ed] != lat[ed]:
            ms_diff_days.append(ed)
        diff = {
            str(d["eval_date"])[:10]: d
            for d in (_load(DAILY_DIFF).get("per_day") or [])
            if isinstance(d, dict)
        }.get(ed, {})
        act = str(diff.get("actual") or "").lower()
        if pa not in ("bull", "bear") or act not in ("bull", "bear"):
            continue
        n += 1
        if pa == act:
            agree_anc += 1
        if pl == act:
            agree_lat += 1
    summary = {
        "n_evaluated": n,
        "anchor_ms_hybrid_rate": round(agree_anc / n, 6) if n else None,
        "latest_ms_hybrid_rate": round(agree_lat / n, 6) if n else None,
        "ms_direction_diff_days": len(ms_diff_days),
        "ms_diff_dates": ms_diff_days[:15],
    }
    out = ROOT / "reports/btrack_ms_anchor_vs_latest_hybrid_v1_latest.json"
    out.write_text(
        json.dumps(
            {"schema": "btrack_ms_anchor_vs_latest_hybrid_v1", "generated_at_utc": _utc(), **summary},
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return {"task": "ms_anchor_vs_latest", "exit_code": 0, "summary": summary}


def _task_hybrid_research_parallel() -> dict[str, Any]:
    script = ROOT / "scripts/run_btrack_hybrid_research_parallel_v1.py"
    if not script.is_file():
        return {"task": "hybrid_research_parallel", "exit_code": 2, "error": "missing script"}
    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    out = ROOT / "reports/btrack_hybrid_research_parallel_v1_latest.json"
    summary: dict[str, Any] = {"exit_code": proc.returncode}
    if out.is_file():
        doc = _load(out)
        summary["lane"] = doc.get("lane")
        summary["operator_lines"] = (doc.get("operator_lines") or [])[:4]
    return {
        "task": "hybrid_research_parallel",
        "exit_code": 0 if proc.returncode in (0, 1) else proc.returncode,
        "summary": summary,
        "stderr_tail": (proc.stderr or "")[-300:] if proc.returncode not in (0, 1) else None,
    }


def _anchor_dates_list() -> list[str]:
    anchor_dates_path = ROOT / "reports/btrack_anchor_eval_dates_v1.json"
    if anchor_dates_path.is_file():
        d = list(_load(anchor_dates_path).get("eval_dates") or [])
        if d:
            return sorted(str(x)[:10] for x in d)
    return sorted(_dir_map(_load(ANCHOR_SCORE)).keys())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    WORK.mkdir(parents=True, exist_ok=True)

    tasks = [
        _task_hybrid_rule_matrix,
        _task_train_miss_autopsy,
        _task_shadow_lane_pack,
        _task_ms_anchor_vs_latest,
        _task_hybrid_research_parallel,
        _task_observation_refresh,
    ]
    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=6) as pool:
        futs = {pool.submit(fn): fn.__name__ for fn in tasks}
        for fut in as_completed(futs):
            try:
                results.append(fut.result())
            except Exception as exc:
                results.append({"task": futs[fut], "exit_code": 2, "error": str(exc)})

    bundle = {
        "schema": "btrack_frozen30d_parallel_bundle_v10",
        "generated_at_utc": _utc(),
        "research_only": True,
        "recommended_lane": "bbs_ms_agree_or_ms_else_v1",
        "parallel_tasks": results,
    }
    args.output.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    for r in results:
        print(f"  {r.get('task')}: exit={r.get('exit_code')} {r.get('summary', r.get('error', ''))}")
    return 0 if all(int(r.get("exit_code", 1)) == 0 for r in results) else 2


if __name__ == "__main__":
    raise SystemExit(main())
